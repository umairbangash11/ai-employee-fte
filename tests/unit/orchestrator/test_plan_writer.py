"""Unit tests for orchestrator.plan_writer.

No OpenAI, no watchdog, no vault filesystem required.
All tests use pytest's tmp_path fixture.
"""

import stat
import pytest
from pathlib import Path

from orchestrator.plan_writer import write_runtime_plan, _safe_slug, _deduplicate_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ACTIONABLE_META = {
    "sender": "alice@example.com",
    "subject": "Re: Project Update",
    "source": "gmail",
    "urgency": "normal",
}

ACTIONABLE_CLASSIFICATION = {
    "needs_reply": True,
    "reason": "Sender asked a direct question.",
    "draft": "Dear Alice, thanks for reaching out...",
}

ERROR_CLASSIFICATION = {
    "needs_reply": False,
    "reason": "Classification failed after 3 retries.",
    "draft": None,
}


# ---------------------------------------------------------------------------
# Phase 3 — US1: Plan created for actionable email
# ---------------------------------------------------------------------------


def test_plan_created_for_actionable_email(tmp_path):
    """T006 — File is created inside plans_dir when needs_reply=True."""
    result = write_runtime_plan(
        plans_dir=tmp_path,
        source_filename="test-email.md",
        email_meta=ACTIONABLE_META,
        classification=ACTIONABLE_CLASSIFICATION,
    )
    assert result is not None
    assert result.exists()
    assert result.parent == tmp_path


def test_all_required_fields_present(tmp_path):
    """T007 — All 7 YAML frontmatter fields are present in the written file."""
    result = write_runtime_plan(
        plans_dir=tmp_path,
        source_filename="test-email.md",
        email_meta=ACTIONABLE_META,
        classification=ACTIONABLE_CLASSIFICATION,
    )
    content = result.read_text(encoding="utf-8")

    required_fields = [
        "type:",
        "status:",
        "created_at:",
        "source_file:",
        "requires_approval:",
        "email_sender:",
        "email_subject:",
    ]
    for field in required_fields:
        assert field in content, f"Missing frontmatter field: {field}"


def test_correct_vault_location(tmp_path):
    """T008 — Plan file is written inside the supplied plans_dir (Needs_Action/plans/)."""
    plans_dir = tmp_path / "Needs_Action" / "plans"
    result = write_runtime_plan(
        plans_dir=plans_dir,
        source_filename="test-email.md",
        email_meta=ACTIONABLE_META,
        classification=ACTIONABLE_CLASSIFICATION,
    )
    assert result is not None
    # Must be inside Needs_Action/plans/ — not Approved/, not Inbox/
    assert result.parent == plans_dir
    assert "Needs_Action" in str(result)
    assert "Approved" not in str(result)
    assert "Inbox" not in str(result)


def test_expected_markdown_structure(tmp_path):
    """T009 — All 6 required Markdown sections are present."""
    result = write_runtime_plan(
        plans_dir=tmp_path,
        source_filename="test-email.md",
        email_meta=ACTIONABLE_META,
        classification=ACTIONABLE_CLASSIFICATION,
    )
    content = result.read_text(encoding="utf-8")

    required_sections = [
        "# Triage Plan",
        "## Objective",
        "## Source Context",
        "## Action Steps",
        "## Approval Requirement",
        "## Status",
    ]
    for section in required_sections:
        assert section in content, f"Missing markdown section: {section}"


def test_standard_action_steps_for_reply_needed(tmp_path):
    """T010 — Three standard checkboxes are present for reply-needed email."""
    result = write_runtime_plan(
        plans_dir=tmp_path,
        source_filename="test-email.md",
        email_meta=ACTIONABLE_META,
        classification=ACTIONABLE_CLASSIFICATION,
    )
    content = result.read_text(encoding="utf-8")

    assert "- [ ] Review the AI-generated draft reply in Needs_Action/drafts/" in content
    assert "- [ ] Edit the draft as needed" in content
    assert "- [ ] Approve by moving to Approved/email/ to authorise sending" in content


# ---------------------------------------------------------------------------
# Phase 5 — US3: Edge cases and independent testability
# ---------------------------------------------------------------------------


def test_filename_deduplication(tmp_path):
    """T016 — Second call with identical subject produces a distinct filename."""
    result1 = write_runtime_plan(
        plans_dir=tmp_path,
        source_filename="email.md",
        email_meta=ACTIONABLE_META,
        classification=ACTIONABLE_CLASSIFICATION,
    )
    result2 = write_runtime_plan(
        plans_dir=tmp_path,
        source_filename="email.md",
        email_meta=ACTIONABLE_META,
        classification=ACTIONABLE_CLASSIFICATION,
    )
    assert result1 is not None
    assert result2 is not None
    assert result1 != result2
    assert result1.exists()
    assert result2.exists()
    # Second file should have a _1 suffix before .md
    assert "_1" in result2.name


def test_error_classification_uses_fallback_steps(tmp_path):
    """T017 — Error/fallback classification produces the two fallback checkboxes."""
    result = write_runtime_plan(
        plans_dir=tmp_path,
        source_filename="test-email.md",
        email_meta=ACTIONABLE_META,
        classification=ERROR_CLASSIFICATION,
    )
    assert result is not None
    content = result.read_text(encoding="utf-8")

    assert "Human review required" in content
    assert "automated classification failed" in content
    assert "Inspect the source email" in content
    # Standard steps must NOT be present
    assert "Review the AI-generated draft reply" not in content


def test_write_failure_returns_none(tmp_path):
    """T018 — Read-only plans_dir causes write failure; None returned, no exception."""
    plans_dir = tmp_path / "readonly_plans"
    plans_dir.mkdir()
    # Remove write permission
    plans_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

    try:
        result = write_runtime_plan(
            plans_dir=plans_dir,
            source_filename="test-email.md",
            email_meta=ACTIONABLE_META,
            classification=ACTIONABLE_CLASSIFICATION,
        )
        assert result is None
    finally:
        # Restore permissions so tmp_path cleanup works
        plans_dir.chmod(stat.S_IRWXU)


def test_plans_dir_created_if_missing(tmp_path):
    """T019 — Non-existent plans_dir is created automatically."""
    plans_dir = tmp_path / "deep" / "nested" / "plans"
    assert not plans_dir.exists()

    result = write_runtime_plan(
        plans_dir=plans_dir,
        source_filename="test-email.md",
        email_meta=ACTIONABLE_META,
        classification=ACTIONABLE_CLASSIFICATION,
    )
    assert result is not None
    assert plans_dir.exists()
    assert result.exists()


def test_requires_approval_always_true(tmp_path):
    """T020 — requires_approval: true in frontmatter regardless of classification."""
    for classification in [ACTIONABLE_CLASSIFICATION, ERROR_CLASSIFICATION]:
        result = write_runtime_plan(
            plans_dir=tmp_path,
            source_filename="test-email.md",
            email_meta=ACTIONABLE_META,
            classification=classification,
        )
        content = result.read_text(encoding="utf-8")
        assert "requires_approval: true" in content


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_safe_slug_basic():
    assert _safe_slug("Re: Project Update") == "re-project-update"


def test_safe_slug_truncates_at_40():
    long = "a" * 50
    assert len(_safe_slug(long)) <= 40


def test_safe_slug_strips_hyphens():
    assert not _safe_slug("---hello---").startswith("-")
    assert not _safe_slug("---hello---").endswith("-")


def test_deduplicate_path_no_conflict(tmp_path):
    path = _deduplicate_path(tmp_path, "plan.md")
    assert path == tmp_path / "plan.md"


def test_deduplicate_path_with_conflict(tmp_path):
    (tmp_path / "plan.md").write_text("x")
    path = _deduplicate_path(tmp_path, "plan.md")
    assert path == tmp_path / "plan_1.md"
