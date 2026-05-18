from specialized.ticket_compliance.extractor import extract_ticket_refs


def test_bare_hash_ref_in_title():
    refs = extract_ticket_refs("#42: add rate limiting", "")
    assert ("github_issues", "42") in refs


def test_closes_keyword_in_body():
    refs = extract_ticket_refs("add rate limiting", "Closes #7\nSee also #12")
    assert ("github_issues", "7") in refs
    assert ("github_issues", "12") in refs


def test_fixes_keyword():
    refs = extract_ticket_refs("add feature", "Fixes #99")
    assert ("github_issues", "99") in refs


def test_resolves_keyword():
    refs = extract_ticket_refs("add feature", "Resolves #3")
    assert ("github_issues", "3") in refs


def test_no_refs_returns_empty():
    refs = extract_ticket_refs("chore: update lockfile", "")
    assert refs == []


def test_deduplicates():
    refs = extract_ticket_refs("#10 #10", "#10")
    gh_refs = [r for r in refs if r == ("github_issues", "10")]
    assert len(gh_refs) == 1


def test_ignores_hash_inside_url():
    refs = extract_ticket_refs("fix something", "See https://github.com/org/repo/issues/42#issuecomment-123")
    for _, ticket_id in refs:
        assert "issuecomment" not in ticket_id
