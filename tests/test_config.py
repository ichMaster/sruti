import pytest

from sruti.config import DEFAULT_RECEIVER, Config, ConfigError, LinkConfig, ReceiverConfig, load_config, parse_env


def test_defaults_without_files(tmp_path):
    config = load_config(tmp_path / "sruti.toml", tmp_path / ".env")
    assert config.receiver == ReceiverConfig()
    assert config.receiver.host_port == DEFAULT_RECEIVER
    assert config.link == LinkConfig()
    assert not config.secrets.gemini and not config.secrets.anthropic


def test_toml_overrides_key_by_key(tmp_path):
    (tmp_path / "sruti.toml").write_text(
        '[receiver]\nfreq_khz = 14100\npassband = [200, 2800]\n[link]\nbusy_retry_s = 45\n', encoding="utf-8")
    config = load_config(tmp_path / "sruti.toml", tmp_path / ".env")
    assert config.receiver.freq_khz == 14100.0
    assert config.receiver.passband == (200, 2800)
    assert config.receiver.host_port == DEFAULT_RECEIVER  # untouched keys keep their defaults
    assert config.link.busy_retry_s == 45.0
    assert config.link.reconnect_max_s == LinkConfig().reconnect_max_s


@pytest.mark.parametrize("toml, fragment", [
    ('[receiver]\nfreq_khz = 50\n', "frequency"),
    ('[receiver]\nhost_port = "no-port"\n', "host:port"),
    ('[receiver]\npassband = [700, 300]\n', "passband"),
    ('[receiver]\ncolour = "red"\n', "unknown key"),
    ('[radio]\nx = 1\n', "unknown section"),
    ('[link]\nreconnect_initial_s = 90\n', "reconnect_initial_s"),
    ('[link]\nkeepalive_s = "fast"\n', "number"),
    ('[receiver\n', "sruti.toml"),
])
def test_invalid_toml_is_a_config_error(tmp_path, toml, fragment):
    (tmp_path / "sruti.toml").write_text(toml, encoding="utf-8")
    with pytest.raises(ConfigError, match=fragment):
        load_config(tmp_path / "sruti.toml", tmp_path / ".env")


def test_env_parser_handles_comments_and_quotes():
    env = parse_env(
        "# a comment\n"
        "GEMINI_API_KEY=abc123 # inline comment\n"
        "ANTHROPIC_API_KEY='quoted value' # c\n"
        "EMPTY=\n"
        "not a pair\n")
    assert env == {"GEMINI_API_KEY": "abc123", "ANTHROPIC_API_KEY": "quoted value", "EMPTY": ""}


def test_keys_never_appear_in_repr_or_str(tmp_path):
    (tmp_path / ".env").write_text("GEMINI_API_KEY=secret-gemini-value\nANTHROPIC_API_KEY=secret-claude\n",
                                   encoding="utf-8")
    config = load_config(tmp_path / "sruti.toml", tmp_path / ".env")
    assert config.secrets.gemini == "secret-gemini-value"
    for text in (repr(config), str(config), repr(config.secrets), str(config.secrets)):
        assert "secret-gemini-value" not in text and "secret-claude" not in text
    assert "gemini=set" in repr(config.secrets) and "anthropic=set" in repr(config.secrets)


def test_missing_keys_are_reported_missing(tmp_path):
    (tmp_path / ".env").write_text("GEMINI_API_KEY=x\n", encoding="utf-8")
    assert "anthropic=missing" in repr(load_config(tmp_path / "sruti.toml", tmp_path / ".env").secrets)


def test_config_is_immutable():
    with pytest.raises(AttributeError):
        Config().receiver.freq_khz = 1.0  # type: ignore[misc]
