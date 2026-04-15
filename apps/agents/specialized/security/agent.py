from __future__ import annotations

import asyncio
import json
import math
import re
from collections import Counter
from pathlib import Path
from random import randint

from .schemas import (
    AgentTask,
    DependencyHit,
    DiffLine,
    Finding,
    RawFinding,
    ReflectionAction,
    ReflectionDecision,
    ReviewResult,
    SastHit,
    ScannerHits,
    SecretHit,
    SecurityContext,
    Severity,
)

SYSTEM_PROMPT = (
    "You are a security-focused code reviewer. Analyze the diff and return JSON findings. "
    "Cite OWASP categories. Never report style issues."
)

REFLECTION_PROMPT = (
    "Review findings on exploit realism, severity proportionality, and confidence >= 0.6. "
    "Keep, drop, or downgrade each."
)


def run_security_agent(task: AgentTask) -> ReviewResult:
    ctx = _build_context(task)
    diff_lines = _extract_added_lines(task.diff, task.repo_config.exempt_paths)
    hits = asyncio.run(_run_scanners(diff_lines))
    _ = _build_generation_prompt(task.diff, hits, ctx)
    raw_findings = _generate_findings(hits)
    _ = _build_reflection_prompt(raw_findings)
    findings = _reflect_findings(raw_findings)
    return _format_output(findings, task)


def _build_context(task: AgentTask) -> SecurityContext:
    rules_dir = Path(__file__).resolve().parent / "rules"
    owasp_rules = _load_json(rules_dir / "owasp_top10_2021.json")

    lang_rules = {}
    languages = _detect_languages(task.diff)
    if "python" in languages:
        lang_rules["python"] = _load_json(rules_dir / "sast_rules_python.json")
    if "javascript" in languages:
        lang_rules["javascript"] = _load_json(rules_dir / "sast_rules_javascript.json")

    return SecurityContext(
        system_prompt=SYSTEM_PROMPT,
        owasp_rules=owasp_rules,
        lang_rules=lang_rules,
        exempt_paths=task.repo_config.exempt_paths,
        severity_overrides=task.repo_config.severity_overrides,
    )


async def _run_scanners(diff_lines: list[DiffLine]) -> ScannerHits:
    secrets_task = asyncio.to_thread(_scan_secrets, diff_lines)
    sast_task = asyncio.to_thread(_scan_sast, diff_lines)
    deps_task = asyncio.to_thread(_scan_dependencies, diff_lines)
    secrets, sast, dependencies = await asyncio.gather(secrets_task, sast_task, deps_task)
    return ScannerHits(secrets=secrets, sast=sast, dependencies=dependencies)


def _build_generation_prompt(diff: str, hits: ScannerHits, ctx: SecurityContext) -> str:
    lines: list[str] = []
    for hit in hits.sast:
        lines.append(
            f"[SAST] {hit.file}:{hit.line} {hit.rule_id} {hit.owasp_id} {hit.severity_hint.value}"
        )
    for hit in hits.secrets:
        lines.append(f"[SECRET] {hit.file}:{hit.line} {hit.pattern_name} {hit.severity_hint.value}")
    for hit in hits.dependencies:
        lines.append(f"[DEP] {hit.package}@{hit.version} {hit.cve_id} {hit.cvss_score}")

    schema = "file, line, category, owasp_id, severity, exploit_path, message, suggested_fix, conf"
    return (
        f"[SYSTEM]\n{ctx.system_prompt}\n\n"
        f"OWASP:\n{json.dumps(ctx.owasp_rules)}\n\n"
        f"Language rules:\n{json.dumps(ctx.lang_rules)}\n\n"
        "[USER]\n"
        f"Schema: {{{schema}}}\n\n"
        f"Diff:\n{diff}\n\n"
        f"Scanner hits:\n{chr(10).join(lines)}"
    )


def _build_reflection_prompt(raw_findings: list[RawFinding]) -> str:
    return (
        f"[SYSTEM]\n{REFLECTION_PROMPT}\n\n"
        "[USER]\nReturn decisions: {finding_index, action, reason, revised_severity?}\n\n"
        f"Findings:\n{json.dumps([f.model_dump(mode='json') for f in raw_findings])}"
    )


def _generate_findings(hits: ScannerHits) -> list[RawFinding]:
    findings: list[RawFinding] = []

    for hit in hits.sast:
        findings.append(
            RawFinding(
                file=hit.file,
                line=hit.line,
                category="Injection",
                owasp_id=hit.owasp_id,
                severity=hit.severity_hint,
                exploit_path="User input may flow to a dangerous sink.",
                message=f"Potential security issue matched SAST rule {hit.rule_id}.",
                suggested_fix="Use parameterized APIs and strict input validation.",
                confidence=0.82,
            )
        )

    for hit in hits.secrets:
        findings.append(
            RawFinding(
                file=hit.file,
                line=hit.line,
                category="Hardcoded Secret",
                owasp_id="A02:2021",
                severity=hit.severity_hint,
                exploit_path="Hardcoded secret could be extracted and abused.",
                message=f"Potential secret detected by pattern {hit.pattern_name}.",
                suggested_fix="Move secret to environment variable or secret manager.",
                confidence=0.93 if hit.pattern_name != "high_entropy_token" else 0.67,
            )
        )

    for hit in hits.dependencies:
        findings.append(
            RawFinding(
                file="dependency-manifest",
                line=1,
                category="Vulnerable Components",
                owasp_id="A06:2021",
                severity=hit.severity_hint,
                exploit_path=f"Dependency {hit.package} is affected by {hit.cve_id}.",
                message=f"Dependency {hit.package}@{hit.version} is vulnerable ({hit.cve_id}).",
                suggested_fix=f"Upgrade {hit.package} to {hit.fix_version or 'a patched version'}.",
                confidence=0.88,
            )
        )

    return findings


def _reflect_findings(raw_findings: list[RawFinding]) -> list[Finding]:
    decisions: list[ReflectionDecision] = []

    for index, finding in enumerate(raw_findings):
        if finding.confidence < 0.60:
            decisions.append(
                ReflectionDecision(
                    finding_index=index,
                    action=ReflectionAction.DROP,
                    reason="Confidence below threshold.",
                )
            )
            continue

        if finding.severity == Severity.CRITICAL and finding.confidence < 0.8:
            decisions.append(
                ReflectionDecision(
                    finding_index=index,
                    action=ReflectionAction.DOWNGRADE,
                    reason="Critical severity unsupported by confidence.",
                    revised_severity=Severity.HIGH,
                )
            )
            continue

        decisions.append(
            ReflectionDecision(
                finding_index=index,
                action=ReflectionAction.KEEP,
                reason="Exploit path and confidence are acceptable.",
            )
        )

    findings: list[Finding] = []
    for decision in decisions:
        candidate = raw_findings[decision.finding_index]
        if decision.action == ReflectionAction.DROP:
            continue

        severity = candidate.severity
        if decision.action == ReflectionAction.DOWNGRADE and decision.revised_severity:
            severity = decision.revised_severity

        findings.append(
            Finding(
                file=candidate.file,
                line=candidate.line,
                severity=severity,
                owasp_id=candidate.owasp_id,
                category=candidate.category,
                message=candidate.message,
                suggested_fix=candidate.suggested_fix,
                confidence=candidate.confidence,
            )
        )

    return findings


def _format_output(findings: list[Finding], task: AgentTask) -> ReviewResult:
    return ReviewResult(
        review_id=f"rev-{randint(100000, 999999)}",
        pr_number=task.pr_number,
        repo=task.repo_id,
        findings=findings,
    )


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _detect_languages(diff: str) -> set[str]:
    found: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("+++ ") and line.endswith(".py"):
            found.add("python")
        if line.startswith("+++ ") and (line.endswith(".js") or line.endswith(".ts")):
            found.add("javascript")
    return found


def _extract_added_lines(diff: str, exempt_paths: list[str]) -> list[DiffLine]:
    current_file = ""
    new_line = 0
    parsed: list[DiffLine] = []

    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw.removeprefix("+++ b/").strip()
            continue

        if raw.startswith("@@"):
            plus = raw.split("+", 1)[1].split(" ", 1)[0]
            new_line = int(plus.split(",", 1)[0])
            continue

        if not current_file:
            continue

        if any(current_file.startswith(prefix) for prefix in exempt_paths):
            if raw.startswith("+") and not raw.startswith("+++"):
                new_line += 1
            elif not raw.startswith("-"):
                new_line += 1
            continue

        if raw.startswith("+") and not raw.startswith("+++"):
            parsed.append(DiffLine(file=current_file, line=new_line, content=raw[1:]))
            new_line += 1
            continue

        if not raw.startswith("-"):
            new_line += 1

    return parsed


def _scan_secrets(diff_lines: list[DiffLine]) -> list[SecretHit]:
    patterns: list[tuple[str, re.Pattern[str], Severity]] = [
        ("stripe_live_key", re.compile(r"sk_live_[A-Za-z0-9]{10,}"), Severity.CRITICAL),
        ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), Severity.HIGH),
        ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), Severity.HIGH),
        ("rsa_private_key", re.compile(r"-----BEGIN RSA PRIVATE KEY-----"), Severity.CRITICAL),
        (
            "hardcoded_password",
            re.compile(r"password\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
            Severity.MEDIUM,
        ),
    ]

    hits: list[SecretHit] = []
    for line in diff_lines:
        for name, pattern, severity in patterns:
            match = pattern.search(line.content)
            if match:
                token = match.group(0)
                hits.append(
                    SecretHit(
                        file=line.file,
                        line=line.line,
                        matched_value=token,
                        pattern_name=name,
                        entropy=_shannon_entropy(token),
                        severity_hint=severity,
                    )
                )

        for token in re.findall(r"[A-Za-z0-9_\-]{20,}", line.content):
            entropy = _shannon_entropy(token)
            if entropy > 3.8 and _looks_like_secret_token(token):
                hits.append(
                    SecretHit(
                        file=line.file,
                        line=line.line,
                        matched_value=token,
                        pattern_name="high_entropy_token",
                        entropy=entropy,
                        severity_hint=Severity.HIGH,
                    )
                )

    dedup: dict[tuple[str, int, str, str], SecretHit] = {}
    for hit in hits:
        key = (hit.file, hit.line, hit.pattern_name, hit.matched_value)
        if key not in dedup:
            dedup[key] = hit
    return list(dedup.values())


def _scan_sast(diff_lines: list[DiffLine]) -> list[SastHit]:
    rules_py = [
        (
            "SQL_FORMAT_STRING",
            re.compile(
                r"(?i)(f\"[^\"]*(select|insert|update|delete)|select\s+.*\{[a-zA-Z0-9_]+\})"
            ),
            "A03:2021",
            Severity.HIGH,
        ),
        ("DANGEROUS_EVAL", re.compile(r"\beval\s*\("), "A03:2021", Severity.HIGH),
        ("DANGEROUS_EXEC", re.compile(r"\bexec\s*\("), "A03:2021", Severity.HIGH),
        (
            "SUBPROCESS_SHELL_TRUE",
            re.compile(r"subprocess\.[a-z_]+\(.*shell\s*=\s*True"),
            "A03:2021",
            Severity.HIGH,
        ),
    ]
    rules_js = [
        ("INNER_HTML_ASSIGNMENT", re.compile(r"\.innerHTML\s*="), "A03:2021", Severity.MEDIUM),
        ("JS_EVAL", re.compile(r"\beval\s*\("), "A03:2021", Severity.HIGH),
    ]

    hits: list[SastHit] = []
    for line in diff_lines:
        language = (
            "python"
            if line.file.endswith(".py")
            else "javascript"
            if line.file.endswith(".js") or line.file.endswith(".ts")
            else "unknown"
        )
        active = rules_py if language == "python" else rules_js if language == "javascript" else []

        for rule_id, pattern, owasp, severity in active:
            if pattern.search(line.content):
                hits.append(
                    SastHit(
                        file=line.file,
                        line=line.line,
                        rule_id=rule_id,
                        owasp_id=owasp,
                        severity_hint=severity,
                    )
                )

    dedup: dict[tuple[str, int, str], SastHit] = {}
    for hit in hits:
        key = (hit.file, hit.line, hit.rule_id)
        if key not in dedup:
            dedup[key] = hit
    return list(dedup.values())


def _scan_dependencies(diff_lines: list[DiffLine]) -> list[DependencyHit]:
    cves = _load_json(Path(__file__).resolve().parent / "rules" / "dependency_cves.json")
    hits: list[DependencyHit] = []

    for line in diff_lines:
        file_name = line.file.rsplit("/", 1)[-1]

        if file_name == "requirements.txt":
            req = re.match(r"^\s*([a-zA-Z0-9_.\-]+)\s*==\s*([a-zA-Z0-9_.\-]+)", line.content)
            if not req:
                continue
            package = req.group(1).lower()
            version = req.group(2)
            hit = _lookup_cve_hit(cves, package, version)
            if hit:
                hits.append(hit)

        if file_name == "package.json":
            match = re.search(r'"([@a-zA-Z0-9_./\-]+)"\s*:\s*"\^?([0-9][^"]*)"', line.content)
            if not match:
                continue
            package = match.group(1).lower()
            version = match.group(2)
            hit = _lookup_cve_hit(cves, package, version)
            if hit:
                hits.append(hit)

        if file_name == "pyproject.toml":
            pyproject_dep = re.search(
                r'"([a-zA-Z0-9_.\-]+)\s*([<>=!~]{1,2})\s*([0-9][0-9A-Za-z_.\-]*)"', line.content
            )
            if not pyproject_dep:
                continue

            package = pyproject_dep.group(1).lower()
            operator = pyproject_dep.group(2)
            version = pyproject_dep.group(3)

            if operator == "==":
                hit = _lookup_cve_hit(cves, package, version)
            else:
                # For ranges (>=, ~=), fall back to the lower bound as a conservative signal.
                hit = _lookup_cve_hit(cves, package, version)

            if hit:
                hits.append(hit)

    dedup: dict[tuple[str, str, str], DependencyHit] = {}
    for hit in hits:
        key = (hit.package, hit.version, hit.cve_id)
        if key not in dedup:
            dedup[key] = hit
    return list(dedup.values())


def _lookup_cve_hit(cves: dict, package: str, version: str) -> DependencyHit | None:
    key = f"{package}@{version}"
    if key not in cves:
        return None

    item = cves[key]
    cvss_score = float(item["cvss_score"])
    return DependencyHit(
        package=package,
        version=version,
        cve_id=str(item["cve_id"]),
        cvss_score=cvss_score,
        fix_version=str(item.get("fix_version") or ""),
        severity_hint=Severity.MEDIUM if cvss_score < 7 else Severity.HIGH,
    )


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _looks_like_secret_token(token: str) -> bool:
    token_lower = token.lower()

    # Skip common long identifiers and path-like names that are noisy in diffs.
    noisy_prefixes = (
        "argus_",
        "review_",
        "result_",
        "severity_",
        "finding_",
        "dependency_",
        "subprocess_",
        "requirements",
    )
    if token_lower.startswith(noisy_prefixes):
        return False

    if token.count("_") >= 3:
        return False

    has_upper = any(ch.isupper() for ch in token)
    has_lower = any(ch.islower() for ch in token)
    has_digit = any(ch.isdigit() for ch in token)

    # Real secrets are usually mixed-format; plain words with underscores are often not secrets.
    return (has_upper and has_lower and has_digit) or (has_lower and has_digit and "_" not in token)
