"""
Unit tests for the security agent's static scanners and supporting utilities.

All functions under test are pure (no I/O, no LLM) so no mocking is needed.
"""

from specialized.security.agent import (
    _RULES_DIR,
    _apply_decisions,
    _detect_languages,
    _extract_added_lines,
    _fallback_reflect_findings,
    _load_sast_rules,
    _scan_dependencies,
    _scan_sast,
    _scan_secrets,
)
from specialized.security.schemas import (
    DiffLine,
    RawFinding,
    ReflectionAction,
    ReflectionDecision,
    Severity,
)

# Load rules once at module level so all tests share the compiled rules.
_COMPILED_RULES, _EXT_MAP = _load_sast_rules(_RULES_DIR)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lines(*contents: tuple[str, int, str]) -> list[DiffLine]:
    return [DiffLine(file=f, line=ln, content=c) for f, ln, c in contents]


def _raw(severity=Severity.HIGH, confidence=0.9, category="Injection") -> RawFinding:
    return RawFinding(
        file="f.py",
        line=1,
        category=category,
        owasp_id="A03:2021",
        severity=severity,
        exploit_path="x",
        message="x",
        suggested_fix="x",
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# _scan_secrets
# ---------------------------------------------------------------------------


def test_scan_secrets_stripe_live_key():
    lines = _lines(("src/pay.py", 1, 'API_KEY = "sk_live_ABCDEFGHIJ123"'))
    hits = _scan_secrets(lines)
    # The token matches both the stripe pattern and the high-entropy scanner
    names = {h.pattern_name for h in hits}
    assert "stripe_live_key" in names
    stripe_hit = next(h for h in hits if h.pattern_name == "stripe_live_key")
    assert stripe_hit.severity_hint == Severity.CRITICAL


def test_scan_secrets_aws_access_key():
    lines = _lines(("src/aws.py", 5, "key = AKIAIOSFODNN7EXAMPLE"))
    hits = _scan_secrets(lines)
    names = {h.pattern_name for h in hits}
    assert "aws_access_key" in names


def test_scan_secrets_github_pat():
    lines = _lines(("cfg.py", 2, "token = ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabc"))
    hits = _scan_secrets(lines)
    names = {h.pattern_name for h in hits}
    assert "github_pat" in names
    pat_hit = next(h for h in hits if h.pattern_name == "github_pat")
    assert pat_hit.severity_hint == Severity.HIGH


def test_scan_secrets_rsa_private_key():
    lines = _lines(("key.py", 1, "-----BEGIN RSA PRIVATE KEY-----"))
    hits = _scan_secrets(lines)
    names = {h.pattern_name for h in hits}
    assert "rsa_private_key" in names
    rsa_hit = next(h for h in hits if h.pattern_name == "rsa_private_key")
    assert rsa_hit.severity_hint == Severity.CRITICAL


def test_scan_secrets_hardcoded_password():
    lines = _lines(("db.py", 3, 'password = "hunter2"'))
    hits = _scan_secrets(lines)
    names = {h.pattern_name for h in hits}
    assert "hardcoded_password" in names
    assert next(h for h in hits if h.pattern_name == "hardcoded_password").severity_hint == Severity.MEDIUM


def test_scan_secrets_no_hit_on_clean_line():
    lines = _lines(("src/utils.py", 1, "def add(a, b): return a + b"))
    hits = _scan_secrets(lines)
    assert hits == []


def test_scan_secrets_dedup_same_secret_same_line():
    line = DiffLine(file="a.py", line=1, content='KEY = "sk_live_ABCDEFGHIJ123"')
    hits = _scan_secrets([line, line])
    stripe_hits = [h for h in hits if h.pattern_name == "stripe_live_key"]
    assert len(stripe_hits) == 1


# ---------------------------------------------------------------------------
# _scan_sast
# ---------------------------------------------------------------------------


def test_scan_sast_sql_format_string():
    lines = _lines(("db.py", 10, 'query = f"SELECT * FROM users WHERE id = {user_id}"'))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    rule_ids = {h.rule_id for h in hits}
    assert "SQL_FORMAT_STRING" in rule_ids


def test_scan_sast_dangerous_eval_python():
    lines = _lines(("run.py", 3, "result = eval(user_input)"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "DANGEROUS_EVAL" for h in hits)
    assert all(h.severity_hint == Severity.HIGH for h in hits)


def test_scan_sast_dangerous_exec_python():
    lines = _lines(("run.py", 4, "exec(user_code)"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "DANGEROUS_EXEC" for h in hits)


def test_scan_sast_subprocess_shell_true():
    lines = _lines(("shell.py", 7, "subprocess.run(cmd, shell=True)"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "SUBPROCESS_SHELL_TRUE" for h in hits)


def test_scan_sast_js_inner_html():
    lines = _lines(("app.js", 2, "element.innerHTML = userInput"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "INNER_HTML_ASSIGNMENT" for h in hits)
    assert next(h for h in hits if h.rule_id == "INNER_HTML_ASSIGNMENT").severity_hint == Severity.MEDIUM


def test_scan_sast_js_eval():
    lines = _lines(("app.js", 5, "eval(code)"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "JS_EVAL" for h in hits)


def test_scan_sast_ts_file_treated_as_js():
    lines = _lines(("app.ts", 1, "eval(expr)"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "JS_EVAL" for h in hits)


def test_scan_sast_unknown_extension_no_hits():
    lines = _lines(("README.md", 1, "eval(something)"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert hits == []


def test_scan_sast_python_rules_not_applied_to_js():
    lines = _lines(("query.js", 1, 'f"SELECT * FROM {table}"'))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert not any(h.rule_id == "SQL_FORMAT_STRING" for h in hits)


def test_scan_sast_dedup_same_rule_same_line():
    line = DiffLine(file="run.py", line=1, content="eval(a); eval(b)")
    hits = _scan_sast([line, line], _COMPILED_RULES, _EXT_MAP)
    eval_hits = [h for h in hits if h.rule_id == "DANGEROUS_EVAL"]
    assert len(eval_hits) == 1


def test_scan_sast_java_runtime_exec():
    lines = _lines(("App.java", 5, "Runtime.getRuntime().exec(cmd)"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "RUNTIME_EXEC" for h in hits)


def test_scan_sast_go_insecure_skip_verify():
    lines = _lines(("client.go", 12, "InsecureSkipVerify: true,"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "TLS_INSECURE_SKIP_VERIFY" for h in hits)


def test_scan_sast_php_eval():
    lines = _lines(("index.php", 3, "eval($_GET['code']);"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "PHP_EVAL" for h in hits)


def test_scan_sast_c_gets():
    lines = _lines(("main.c", 7, "gets(buffer);"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "GETS_UNSAFE" for h in hits)
    assert any(h.severity_hint == Severity.CRITICAL for h in hits)


def test_scan_sast_ruby_yaml_load():
    lines = _lines(("config.rb", 4, "data = YAML.load(user_input)"))
    hits = _scan_sast(lines, _COMPILED_RULES, _EXT_MAP)
    assert any(h.rule_id == "YAML_UNSAFE_LOAD_RUBY" for h in hits)


# ---------------------------------------------------------------------------
# _scan_dependencies
# ---------------------------------------------------------------------------


def test_scan_dependencies_requirements_txt_vulnerable():
    # jinja2==2.10 is below both 2.10.1 (CVE-2019-10906) and 3.1.3 (CVE-2024-22195)
    lines = _lines(("requirements.txt", 1, "jinja2==2.10"))
    hits = _scan_dependencies(lines)
    cve_ids = {h.cve_id for h in hits}
    assert "CVE-2019-10906" in cve_ids
    hit = next(h for h in hits if h.cve_id == "CVE-2019-10906")
    assert hit.package == "jinja2"
    assert hit.severity_hint == Severity.HIGH  # cvss 7.5 >= 7


def test_scan_dependencies_requirements_txt_safe():
    # requests==2.31.0 is exactly at the fix boundary for CVE-2023-32681 — not affected
    lines = _lines(("requirements.txt", 1, "requests==2.31.0"))
    hits = _scan_dependencies(lines)
    assert hits == []


def test_scan_dependencies_package_json_vulnerable():
    # lodash 4.17.15 is below 4.17.21 — affected by both CVE-2020-8203 and CVE-2021-23337
    lines = _lines(("package.json", 1, '"lodash": "^4.17.15"'))
    hits = _scan_dependencies(lines)
    cve_ids = {h.cve_id for h in hits}
    assert "CVE-2020-8203" in cve_ids
    assert all(h.package == "lodash" for h in hits)


def test_scan_dependencies_package_json_safe():
    # Use a package not in the CVE database to guarantee zero hits
    lines = _lines(("package.json", 1, '"chalk": "^5.3.0"'))
    hits = _scan_dependencies(lines)
    assert hits == []


def test_scan_dependencies_dedup_same_cve():
    # Passing the same line twice must not produce duplicate CVE entries
    line = DiffLine(file="requirements.txt", line=1, content="jinja2==2.10")
    hits = _scan_dependencies([line, line])
    cve_ids = [h.cve_id for h in hits]
    assert len(cve_ids) == len(set(cve_ids)), "Duplicate CVE IDs in hits"
    assert len(hits) >= 1


def test_scan_dependencies_non_manifest_file_ignored():
    lines = _lines(("src/utils.py", 1, "jinja2==2.10"))
    hits = _scan_dependencies(lines)
    assert hits == []


# ---------------------------------------------------------------------------
# _extract_added_lines
# ---------------------------------------------------------------------------


SIMPLE_DIFF = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,4 @@
 def foo():
+    return eval(x)
-    return x
 pass
"""

EXEMPT_DIFF = """\
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1,2 +1,3 @@
+    eval(x)
 pass
"""

MULTI_FILE_DIFF = """\
--- a/src/a.py
+++ b/src/a.py
@@ -1 +1,2 @@
+line_a
--- a/src/b.py
+++ b/src/b.py
@@ -5 +5,2 @@
+line_b
"""


def test_extract_added_lines_captures_additions():
    lines = _extract_added_lines(SIMPLE_DIFF, [])
    contents = [line.content for line in lines]
    assert any("eval" in c for c in contents)


def test_extract_added_lines_ignores_deletions():
    lines = _extract_added_lines(SIMPLE_DIFF, [])
    assert not any("return x" in line.content for line in lines)


def test_extract_added_lines_exempt_path_skipped():
    lines = _extract_added_lines(EXEMPT_DIFF, ["tests/"])
    assert lines == []


def test_extract_added_lines_non_exempt_path_included():
    lines = _extract_added_lines(EXEMPT_DIFF, [])
    assert any("eval" in line.content for line in lines)


def test_extract_added_lines_multi_file_correct_filenames():
    lines = _extract_added_lines(MULTI_FILE_DIFF, [])
    files = {line.file for line in lines}
    assert "src/a.py" in files
    assert "src/b.py" in files


def test_extract_added_lines_correct_line_numbers():
    lines = _extract_added_lines(MULTI_FILE_DIFF, [])
    b_lines = [line for line in lines if line.file == "src/b.py"]
    assert b_lines[0].line == 5


# ---------------------------------------------------------------------------
# _detect_languages
# ---------------------------------------------------------------------------


def test_detect_languages_python():
    diff = "+++ b/src/app.py\n+code"
    assert "python" in _detect_languages(diff, _EXT_MAP)


def test_detect_languages_javascript():
    diff = "+++ b/src/app.js\n+code"
    assert "javascript" in _detect_languages(diff, _EXT_MAP)


def test_detect_languages_typescript():
    diff = "+++ b/src/app.ts\n+code"
    assert "javascript" in _detect_languages(diff, _EXT_MAP)


def test_detect_languages_java():
    diff = "+++ b/src/Main.java\n+code"
    assert "java" in _detect_languages(diff, _EXT_MAP)


def test_detect_languages_go():
    diff = "+++ b/main.go\n+code"
    assert "go" in _detect_languages(diff, _EXT_MAP)


def test_detect_languages_unknown():
    diff = "+++ b/README.md\n+code"
    result = _detect_languages(diff, _EXT_MAP)
    assert "python" not in result
    assert "javascript" not in result


def test_detect_languages_multi():
    diff = "+++ b/src/a.py\n+++ b/src/b.js\n+code"
    result = _detect_languages(diff, _EXT_MAP)
    assert "python" in result
    assert "javascript" in result


# ---------------------------------------------------------------------------
# _fallback_reflect_findings
# ---------------------------------------------------------------------------


def test_fallback_reflect_drops_low_confidence():
    findings = [_raw(confidence=0.5)]
    result = _fallback_reflect_findings(findings)
    assert result == []


def test_fallback_reflect_keeps_normal_finding():
    findings = [_raw(confidence=0.85)]
    result = _fallback_reflect_findings(findings)
    assert len(result) == 1


def test_fallback_reflect_downgrades_critical_low_confidence():
    findings = [_raw(severity=Severity.CRITICAL, confidence=0.75)]
    result = _fallback_reflect_findings(findings)
    assert len(result) == 1
    assert result[0].severity == Severity.HIGH


def test_fallback_reflect_keeps_critical_high_confidence():
    findings = [_raw(severity=Severity.CRITICAL, confidence=0.9)]
    result = _fallback_reflect_findings(findings)
    assert len(result) == 1
    assert result[0].severity == Severity.CRITICAL


def test_fallback_reflect_mixed_findings():
    findings = [
        _raw(confidence=0.4),  # dropped
        _raw(confidence=0.85),  # kept
    ]
    result = _fallback_reflect_findings(findings)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# _apply_decisions
# ---------------------------------------------------------------------------


def test_apply_decisions_downgrade_changes_severity():
    findings = [_raw(severity=Severity.CRITICAL, confidence=0.9)]
    decisions = [
        ReflectionDecision(
            finding_index=0,
            action=ReflectionAction.DOWNGRADE,
            reason="Overstated.",
            revised_severity=Severity.MEDIUM,
        )
    ]
    result = _apply_decisions(findings, decisions)
    assert len(result) == 1
    assert result[0].severity == Severity.MEDIUM


def test_apply_decisions_out_of_range_index_skipped():
    findings = [_raw()]
    decisions = [
        ReflectionDecision(
            finding_index=99,
            action=ReflectionAction.KEEP,
            reason="bogus index",
        )
    ]
    result = _apply_decisions(findings, decisions)
    assert result == []


def test_apply_decisions_negative_index_skipped():
    findings = [_raw()]
    decisions = [
        ReflectionDecision(
            finding_index=-1,
            action=ReflectionAction.KEEP,
            reason="negative index",
        )
    ]
    result = _apply_decisions(findings, decisions)
    assert result == []
