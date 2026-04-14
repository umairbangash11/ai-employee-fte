"""Integration tests for LinkedIn CLI commands."""

import pytest
from pathlib import Path
from click.testing import CliRunner
import json

from linkedin_publisher.__main__ import cli
from linkedin_publisher.state import save_execution_state
from linkedin_publisher.models import ExecutionState
from datetime import datetime


class TestLinkedInCLI:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def vault_setup(self, tmp_path):
        """Setup vault structure for CLI tests."""
        vault_path = tmp_path / "vault"
        (vault_path / "Approved" / "linkedin").mkdir(parents=True)
        (vault_path / "Done" / "linkedin").mkdir(parents=True)
        (vault_path / "Needs_Action" / "linkedin").mkdir(parents=True)
        (vault_path / "Logs" / "linkedin").mkdir(parents=True)

        state_dir = tmp_path / ".watcher-state" / "linkedin"
        state_dir.mkdir(parents=True)

        return {
            "vault_path": vault_path,
            "state_path": state_dir / "publisher.json",
        }

    def test_list_empty(self, vault_setup):
        """Test list command with no pending files."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--vault-path", str(vault_setup["vault_path"]),
            "list",
        ])

        assert result.exit_code == 0
        assert "No approved LinkedIn posts found" in result.output

    def test_list_with_files(self, vault_setup):
        """Test list command with pending files."""
        # Create test files
        approved_dir = vault_setup["vault_path"] / "Approved" / "linkedin"
        (approved_dir / "post1.md").write_text("---\ntype: approval_request\n---\nContent")
        (approved_dir / "post2.md").write_text("---\ntype: approval_request\n---\nContent")

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--vault-path", str(vault_setup["vault_path"]),
            "list",
        ])

        assert result.exit_code == 0
        assert "post1.md" in result.output
        assert "post2.md" in result.output
        assert "2" in result.output  # Count

    def test_status_never_run(self, vault_setup):
        """Test status command when never run before."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--vault-path", str(vault_setup["vault_path"]),
            "status",
        ])

        assert result.exit_code == 0
        assert "Last run: Never" in result.output
        assert "Total published: 0" in result.output

    def test_status_with_history(self, vault_setup):
        """Test status command with publish history."""
        # Create state with history
        state = ExecutionState(
            processed_hashes={"hash1", "hash2", "hash3"},
            last_run=datetime(2026, 3, 12, 10, 0, 0),
            total_published=10,
            total_failed=2,
        )
        save_execution_state(state, vault_setup["state_path"])

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--vault-path", str(vault_setup["vault_path"]),
            "status",
        ])

        assert result.exit_code == 0
        assert "Total published: 10" in result.output
        assert "Total failed: 2" in result.output
        assert "Processed hashes: 3" in result.output

    def test_run_empty(self, vault_setup):
        """Test run command with no files."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--vault-path", str(vault_setup["vault_path"]),
            "run",
        ])

        assert result.exit_code == 0
        assert "No approved LinkedIn posts found" in result.output

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "LinkedIn publisher" in result.output
        assert "run" in result.output
        assert "watch" in result.output
        assert "list" in result.output
        assert "status" in result.output
        assert "auth" in result.output

    def test_run_help(self):
        """Test run command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])

        assert result.exit_code == 0
        assert "Process all approved posts" in result.output

    def test_vault_path_required(self):
        """Test error when vault path not provided."""
        runner = CliRunner()
        result = runner.invoke(cli, ["list"])

        # Should fail with error about VAULT_PATH
        assert result.exit_code != 0 or "VAULT_PATH" in result.output
