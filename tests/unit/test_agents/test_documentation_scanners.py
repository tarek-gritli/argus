"""
Unit tests for the documentation agent's static checks and validator.

All functions under test are pure (no I/O, no LLM calls) so no mocking is needed.
"""

from specialized.documentation.checks.missing_docstrings import run_missing_docstring_checks
from specialized.documentation.checks.param_coverage import run_param_coverage_checks
from specialized.documentation.checks.readme_gaps import run_readme_gap_checks
from specialized.documentation.checks.stale_comments import run_stale_comment_checks
from specialized.documentation.validator import validate_findings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(diff: str, changed_files: dict | None = None) -> dict:
    return {"diff": diff, "changed_files": changed_files or {}}


def _finding(**overrides) -> dict:
    base = {
        "agent": "documentation",
        "severity": "medium",
        "file": "src/foo.py",
        "line_start": 1,
        "line_end": 1,
        "title": "Some issue",
        "description": "Some description.",
        "suggestion": "Fix it like this.",
        "confidence": 0.85,
        "fix": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _run_missing_docstring_checks
# ---------------------------------------------------------------------------

DIFF_DEF_NO_DOCSTRING = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,5 @@
+def process_payment(amount, currency):
+    return amount * 1.2
"""

DIFF_DEF_WITH_DOCSTRING = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,4 +1,6 @@
+def process_payment(amount, currency):
+    \"\"\"Process a payment and return the total.\"\"\"
+    return amount * 1.2
"""

DIFF_PRIVATE_DEF_NO_DOCSTRING = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
+def _internal_helper(x):
+    return x + 1
"""

DIFF_CLASS_NO_DOCSTRING = """\
--- a/src/models.py
+++ b/src/models.py
@@ -1,3 +1,4 @@
+class PaymentProcessor:
+    def charge(self):
+        pass
"""

DIFF_CLASS_WITH_DOCSTRING = """\
--- a/src/models.py
+++ b/src/models.py
@@ -1,4 +1,6 @@
+class PaymentProcessor:
+    \"\"\"Handles payment processing logic.\"\"\"
+    def charge(self):
+        pass
"""

DIFF_ASYNC_DEF_NO_DOCSTRING = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
+async def fetch_data(url):
+    pass
"""


def test_missing_docstring_detects_bare_function():
    hits = run_missing_docstring_checks(_ctx(DIFF_DEF_NO_DOCSTRING))
    titles = [h["title"] for h in hits]
    assert any("process_payment" in t for t in titles)


def test_missing_docstring_no_hit_when_docstring_present():
    hits = run_missing_docstring_checks(_ctx(DIFF_DEF_WITH_DOCSTRING))
    assert not any("process_payment" in h["title"] for h in hits)


def test_missing_docstring_ignores_private_functions():
    hits = run_missing_docstring_checks(_ctx(DIFF_PRIVATE_DEF_NO_DOCSTRING))
    assert hits == []


def test_missing_docstring_detects_class_without_docstring():
    hits = run_missing_docstring_checks(_ctx(DIFF_CLASS_NO_DOCSTRING))
    assert any("PaymentProcessor" in h["title"] for h in hits)


def test_missing_docstring_no_hit_class_with_docstring():
    hits = run_missing_docstring_checks(_ctx(DIFF_CLASS_WITH_DOCSTRING))
    assert not any("PaymentProcessor" in h["title"] for h in hits)


def test_missing_docstring_detects_async_function():
    hits = run_missing_docstring_checks(_ctx(DIFF_ASYNC_DEF_NO_DOCSTRING))
    assert any("fetch_data" in h["title"] for h in hits)


def test_missing_docstring_severity_is_high_for_function():
    hits = run_missing_docstring_checks(_ctx(DIFF_DEF_NO_DOCSTRING))
    fn_hit = next((h for h in hits if "process_payment" in h["title"]), None)
    assert fn_hit is not None
    assert fn_hit["severity"] == "high"


def test_missing_docstring_severity_is_medium_for_class():
    hits = run_missing_docstring_checks(_ctx(DIFF_CLASS_NO_DOCSTRING))
    cls_hit = next((h for h in hits if "PaymentProcessor" in h["title"]), None)
    assert cls_hit is not None
    assert cls_hit["severity"] == "medium"


def test_missing_docstring_clean_diff_no_hits():
    diff = "+++ b/src/app.py\n+x = 1 + 2\n"
    hits = run_missing_docstring_checks(_ctx(diff))
    assert hits == []


# ---------------------------------------------------------------------------
# run_stale_comment_checks
# ---------------------------------------------------------------------------

DIFF_TODO_NO_TICKET = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
+    # TODO: add retry logic
+    pass
"""

DIFF_TODO_WITH_TICKET = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
+    # TODO(PROJ-123): add retry logic
+    pass
"""

DIFF_FIXME = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
+    # FIXME: this is broken
+    pass
"""

DIFF_COMMENTED_CODE = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
+    # result = old_generate(data)
+    pass
"""

DIFF_NO_DEBT = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
+    # This converts cents to dollars for display purposes
+    amount = cents / 100
"""


def test_stale_comments_detects_todo_no_ticket():
    hits = run_stale_comment_checks(_ctx(DIFF_TODO_NO_TICKET))
    assert any("TODO" in h["title"] for h in hits)


def test_stale_comments_todo_no_ticket_is_medium_severity():
    hits = run_stale_comment_checks(_ctx(DIFF_TODO_NO_TICKET))
    hit = next((h for h in hits if "TODO" in h["title"]), None)
    assert hit is not None
    assert hit["severity"] == "medium"


def test_stale_comments_todo_with_ticket_is_low_severity():
    hits = run_stale_comment_checks(_ctx(DIFF_TODO_WITH_TICKET))
    hit = next((h for h in hits if "TODO" in h["title"]), None)
    assert hit is not None
    assert hit["severity"] == "low"


def test_stale_comments_detects_fixme():
    hits = run_stale_comment_checks(_ctx(DIFF_FIXME))
    assert any("FIXME" in h["title"] for h in hits)


def test_stale_comments_detects_commented_out_code():
    hits = run_stale_comment_checks(_ctx(DIFF_COMMENTED_CODE))
    assert any("Commented-out" in h["title"] for h in hits)


def test_stale_comments_clean_comment_no_hit():
    hits = run_stale_comment_checks(_ctx(DIFF_NO_DEBT))
    assert hits == []


def test_stale_comments_ignores_deleted_lines():
    diff = "--- a/src/app.py\n+++ b/src/app.py\n@@ -1,2 +1,2 @@\n-    # TODO: old task\n+    pass\n"
    hits = run_stale_comment_checks(_ctx(diff))
    assert hits == []


# ---------------------------------------------------------------------------
# run_param_coverage_checks
# ---------------------------------------------------------------------------

DIFF_PARAMS_NO_ARGS_SECTION = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,5 +1,7 @@
+def create_user(username, email, role):
+    \"\"\"Create a new user in the system.\"\"\"
+    return {"username": username}
"""

DIFF_PARAMS_WITH_ARGS_SECTION = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,7 +1,10 @@
+def create_user(username, email, role):
+    \"\"\"Create a new user.
+
+    Args:
+        username: The username.
+        email: The email.
+        role: The role.
+    \"\"\"
+    return {"username": username}
"""

DIFF_RETURN_HINT_NO_RETURNS_SECTION = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,4 +1,6 @@
+def get_total(amount: float, tax: float) -> float:
+    \"\"\"Compute the total amount including tax.
+
+    Args:
+        amount: Base amount.
+        tax: Tax rate.
+    \"\"\"
+    return amount * (1 + tax)
"""

DIFF_NO_PARAMS_SELF_ONLY = """\
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,4 @@
+def run(self):
+    \"\"\"Run the processor.\"\"\"
+    pass
"""


def test_param_coverage_detects_missing_args_section():
    hits = run_param_coverage_checks(_ctx(DIFF_PARAMS_NO_ARGS_SECTION))
    assert any("create_user" in h["title"] for h in hits)


def test_param_coverage_no_hit_when_args_section_present():
    hits = run_param_coverage_checks(_ctx(DIFF_PARAMS_WITH_ARGS_SECTION))
    assert not any("create_user" in h["title"] for h in hits)


def test_param_coverage_detects_missing_returns_section():
    hits = run_param_coverage_checks(_ctx(DIFF_RETURN_HINT_NO_RETURNS_SECTION))
    assert any("Returns" in h["title"] for h in hits)


def test_param_coverage_ignores_self_only_functions():
    hits = run_param_coverage_checks(_ctx(DIFF_NO_PARAMS_SELF_ONLY))
    assert hits == []


def test_param_coverage_severity_is_medium():
    hits = run_param_coverage_checks(_ctx(DIFF_PARAMS_NO_ARGS_SECTION))
    if hits:
        assert all(h["severity"] == "medium" for h in hits)


# ---------------------------------------------------------------------------
# run_readme_gap_checks
# ---------------------------------------------------------------------------

NEW_MODULE_DIFF = """\
--- /dev/null
+++ b/src/payment_service.py
@@ -0,0 +1,3 @@
+def charge(amount):
+    pass
"""

NEW_MODULE_WITH_DOC_DIFF = """\
--- /dev/null
+++ b/src/payment_service.py
@@ -0,0 +1,3 @@
+def charge(amount):
+    pass
--- a/README.md
+++ b/README.md
@@ -1,1 +1,2 @@
+## Payment Service
"""

ENV_VAR_DIFF = """\
--- a/src/config.py
+++ b/src/config.py
@@ -1,2 +1,3 @@
+import os
+DATABASE_URL = os.environ.get("DATABASE_URL")
"""

ENV_VAR_WITH_DOC_DIFF = """\
--- a/src/config.py
+++ b/src/config.py
@@ -1,2 +1,3 @@
+DATABASE_URL = os.environ.get("DATABASE_URL")
--- a/README.md
+++ b/README.md
@@ -1,1 +1,2 @@
+DATABASE_URL: required
"""


def test_readme_gap_detects_new_module_without_docs():
    changed = {"src/payment_service.py": "def charge(amount): pass"}
    hits = run_readme_gap_checks(_ctx(NEW_MODULE_DIFF, changed))
    assert any("payment_service" in h["title"] for h in hits)


def test_readme_gap_no_hit_when_readme_updated():
    changed = {"src/payment_service.py": "def charge(amount): pass", "README.md": "## Payment"}
    hits = run_readme_gap_checks(_ctx(NEW_MODULE_WITH_DOC_DIFF, changed))
    assert not any("payment_service" in h["title"] for h in hits)


def test_readme_gap_detects_undocumented_env_var():
    changed = {"src/config.py": 'DATABASE_URL = os.environ.get("DATABASE_URL")'}
    hits = run_readme_gap_checks(_ctx(ENV_VAR_DIFF, changed))
    assert any("DATABASE_URL" in h["title"] for h in hits)


def test_readme_gap_env_var_severity_is_high():
    changed = {"src/config.py": 'DATABASE_URL = os.environ.get("DATABASE_URL")'}
    hits = run_readme_gap_checks(_ctx(ENV_VAR_DIFF, changed))
    env_hit = next((h for h in hits if "DATABASE_URL" in h["title"]), None)
    assert env_hit is not None
    assert env_hit["severity"] == "high"


def test_readme_gap_no_hit_when_docs_updated_for_env_var():
    changed = {"src/config.py": "...", "README.md": "DATABASE_URL: required"}
    hits = run_readme_gap_checks(_ctx(ENV_VAR_WITH_DOC_DIFF, changed))
    assert not any("DATABASE_URL" in h["title"] for h in hits)


def test_readme_gap_ignores_test_files():
    diff = "--- /dev/null\n+++ b/tests/test_payment.py\n@@ -0,0 +1 @@\n+pass\n"
    changed = {"tests/test_payment.py": "pass"}
    hits = run_readme_gap_checks(_ctx(diff, changed))
    assert not any("test_payment" in h["title"] for h in hits)


# ---------------------------------------------------------------------------
# validate_findings
# ---------------------------------------------------------------------------


def test_validator_keeps_valid_finding():
    findings = [_finding()]
    result = validate_findings(findings)
    assert len(result) == 1


def test_validator_drops_low_confidence():
    findings = [_finding(confidence=0.4)]
    result = validate_findings(findings)
    assert result == []


def test_validator_drops_finding_without_suggestion():
    findings = [_finding(suggestion="")]
    result = validate_findings(findings)
    assert result == []


def test_validator_drops_missing_required_field():
    findings = [{"agent": "documentation", "severity": "medium"}]
    result = validate_findings(findings)
    assert result == []


def test_validator_normalizes_unknown_severity():
    findings = [_finding(severity="extreme")]
    result = validate_findings(findings)
    assert result[0]["severity"] == "medium"


def test_validator_forces_agent_tag():
    findings = [_finding(agent="wrong")]
    result = validate_findings(findings)
    assert result[0]["agent"] == "documentation"


def test_validator_sorts_by_severity_then_confidence():
    findings = [
        _finding(severity="low", confidence=0.9),
        _finding(severity="high", confidence=0.7),
        _finding(severity="medium", confidence=0.8),
    ]
    result = validate_findings(findings)
    assert result[0]["severity"] == "high"
    assert result[1]["severity"] == "medium"
    assert result[2]["severity"] == "low"


def test_validator_caps_at_max_findings():
    findings = [_finding(title=f"Issue {i}") for i in range(20)]
    result = validate_findings(findings)
    assert len(result) <= 15


def test_validator_penalizes_speculative_findings():
    findings = [_finding(confidence=0.80, description="no documentation exists anywhere")]
    result = validate_findings(findings)
    # confidence 0.80 * 0.5 = 0.40 → below threshold → dropped
    assert result == []


def test_validator_drops_invalid_line_range():
    findings = [_finding(line_start=10, line_end=5)]
    result = validate_findings(findings)
    assert result == []


def test_validator_drops_negative_line_start():
    findings = [_finding(line_start=-1, line_end=1)]
    result = validate_findings(findings)
    assert result == []
