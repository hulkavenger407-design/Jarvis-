import os
from unittest import mock

import pytest
from config.manager import ConfigError, ConfigManager


@pytest.fixture
def manager() -> ConfigManager:
    return ConfigManager({"EXPLICIT_KEY": "explicit_value", "INT_KEY": 42})


def test_get_str_explicit(manager: ConfigManager) -> None:
    assert manager.get_str("EXPLICIT_KEY") == "explicit_value"


def test_get_str_default(manager: ConfigManager) -> None:
    assert manager.get_str("MISSING_KEY", "default_val") == "default_val"


def test_get_str_missing_raises(manager: ConfigManager) -> None:
    with pytest.raises(ConfigError, match="Missing required configuration key"):
        manager.get_str("NOPE")


@mock.patch.dict(os.environ, {"ENV_KEY": "env_value", "EXPLICIT_KEY": "ignored"})
def test_get_str_from_env(manager: ConfigManager) -> None:
    # Env var works
    assert manager.get_str("ENV_KEY") == "env_value"
    # Explicit config overrides env var
    assert manager.get_str("EXPLICIT_KEY") == "explicit_value"


def test_get_int_valid(manager: ConfigManager) -> None:
    assert manager.get_int("INT_KEY") == 42


@mock.patch.dict(os.environ, {"ENV_INT": "100"})
def test_get_int_from_env(manager: ConfigManager) -> None:
    assert manager.get_int("ENV_INT") == 100


def test_get_int_invalid(manager: ConfigManager) -> None:
    with pytest.raises(ConfigError, match="must be an integer"):
        manager.get_int("EXPLICIT_KEY")


def test_get_bool_valid() -> None:
    # Test dictionary boolean extraction
    mgr = ConfigManager({"BOOL_TRUE": True, "BOOL_FALSE": False})
    assert mgr.get_bool("BOOL_TRUE") is True
    assert mgr.get_bool("BOOL_FALSE") is False


@pytest.mark.parametrize("value,expected", [
    ("true", True),
    ("True", True),
    ("1", True),
    ("yes", True),
    ("on", True),
    ("false", False),
    ("0", False),
    ("no", False),
    ("off", False),
    ("random_string", False)
])
def test_get_bool_parsing(value: str, expected: bool) -> None:
    with mock.patch.dict(os.environ, {"TEST_BOOL": value}):
        mgr = ConfigManager()
        assert mgr.get_bool("TEST_BOOL") is expected


def test_get_bool_missing_raises(manager: ConfigManager) -> None:
    with pytest.raises(ConfigError, match="Missing required configuration key"):
        manager.get_bool("NOPE")
