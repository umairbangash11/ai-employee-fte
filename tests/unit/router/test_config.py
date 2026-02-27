"""Tests for router configuration loading."""

import os
from pathlib import Path
from unittest import mock

import pytest

from router.config import RouterConfig, load_router_config


class TestRouterConfig:
    """Tests for RouterConfig dataclass."""

    def test_default_values(self):
        """RouterConfig has sensible defaults."""
        config = RouterConfig()
        assert config.vault_path == Path(".")
        assert config.sla_threshold_hours == 24
        assert "urgent" in config.urgency_keywords
        assert "asap" in config.urgency_keywords
        assert config.verbose_logging is False

    def test_custom_values(self):
        """RouterConfig accepts custom values."""
        config = RouterConfig(
            vault_path=Path("/custom/vault"),
            sla_threshold_hours=4,
            urgency_keywords=["p0", "critical"],
            verbose_logging=True,
        )
        assert config.vault_path == Path("/custom/vault")
        assert config.sla_threshold_hours == 4
        assert config.urgency_keywords == ["p0", "critical"]
        assert config.verbose_logging is True


class TestLoadRouterConfig:
    """Tests for load_router_config function."""

    def test_defaults_when_no_env(self):
        """Returns defaults when no environment variables set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            config = load_router_config()
            assert config.vault_path == Path(".")
            assert config.sla_threshold_hours == 24
            assert "urgent" in config.urgency_keywords
            assert config.verbose_logging is False

    def test_vault_path_from_env(self):
        """Loads VAULT_PATH from environment."""
        with mock.patch.dict(os.environ, {"VAULT_PATH": "/my/vault"}, clear=True):
            config = load_router_config()
            assert config.vault_path == Path("/my/vault")

    def test_sla_hours_from_env(self):
        """Loads ROUTER_SLA_HOURS from environment."""
        with mock.patch.dict(os.environ, {"ROUTER_SLA_HOURS": "4"}, clear=True):
            config = load_router_config()
            assert config.sla_threshold_hours == 4

    def test_sla_hours_minimum_enforced(self):
        """SLA hours cannot be less than 1."""
        with mock.patch.dict(os.environ, {"ROUTER_SLA_HOURS": "0"}, clear=True):
            config = load_router_config()
            assert config.sla_threshold_hours == 1

    def test_sla_hours_invalid_defaults(self):
        """Invalid SLA hours value defaults to 24."""
        with mock.patch.dict(os.environ, {"ROUTER_SLA_HOURS": "invalid"}, clear=True):
            config = load_router_config()
            assert config.sla_threshold_hours == 24

    def test_keywords_from_env(self):
        """Loads ROUTER_URGENCY_KEYWORDS from environment."""
        with mock.patch.dict(
            os.environ,
            {"ROUTER_URGENCY_KEYWORDS": "p0, critical, blocker"},
            clear=True,
        ):
            config = load_router_config()
            assert config.urgency_keywords == ["p0", "critical", "blocker"]

    def test_keywords_empty_uses_defaults(self):
        """Empty keywords string uses default keywords."""
        with mock.patch.dict(os.environ, {"ROUTER_URGENCY_KEYWORDS": ""}, clear=True):
            config = load_router_config()
            assert "urgent" in config.urgency_keywords

    def test_verbose_logging_true(self):
        """Loads ROUTER_VERBOSE_LOG=true from environment."""
        with mock.patch.dict(os.environ, {"ROUTER_VERBOSE_LOG": "true"}, clear=True):
            config = load_router_config()
            assert config.verbose_logging is True

    def test_verbose_logging_yes(self):
        """Loads ROUTER_VERBOSE_LOG=yes from environment."""
        with mock.patch.dict(os.environ, {"ROUTER_VERBOSE_LOG": "yes"}, clear=True):
            config = load_router_config()
            assert config.verbose_logging is True

    def test_verbose_logging_1(self):
        """Loads ROUTER_VERBOSE_LOG=1 from environment."""
        with mock.patch.dict(os.environ, {"ROUTER_VERBOSE_LOG": "1"}, clear=True):
            config = load_router_config()
            assert config.verbose_logging is True

    def test_verbose_logging_false(self):
        """Loads ROUTER_VERBOSE_LOG=false from environment."""
        with mock.patch.dict(os.environ, {"ROUTER_VERBOSE_LOG": "false"}, clear=True):
            config = load_router_config()
            assert config.verbose_logging is False
