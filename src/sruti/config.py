"""Configuration: defaults in code, overridden by an optional `sruti.toml`; API keys from `.env`.

Only whether each key is set ever leaves this module's objects in readable form: a key is never part of
a repr, an error message or any output.
"""

import pathlib
import re
import tomllib
from dataclasses import dataclass, field, fields, replace

DEFAULT_RECEIVER = "sdr.autreradioautreculture.com:8073"
FREQ_RANGE_KHZ = (100.0, 30000.0)
HOST_PORT = re.compile(r"^[A-Za-z0-9.-]+:\d{1,5}$")


class ConfigError(ValueError):
    """A configuration value is missing or invalid. Messages name the key, never a secret's value."""


@dataclass(frozen=True)
class ReceiverConfig:
    host_port: str = DEFAULT_RECEIVER
    freq_khz: float = 7027.5
    passband: tuple[int, int] = (300, 700)
    identity: str = "sruti"


@dataclass(frozen=True)
class LinkConfig:
    reconnect_initial_s: float = 2.0
    reconnect_max_s: float = 60.0
    busy_retry_s: float = 30.0
    keepalive_s: float = 1.0


@dataclass(frozen=True)
class Secrets:
    """The two API keys. The repr says only whether each is set."""

    gemini: str = field(default="", repr=False)
    anthropic: str = field(default="", repr=False)

    def __repr__(self) -> str:
        return (f"Secrets(gemini={'set' if self.gemini else 'missing'}, "
                f"anthropic={'set' if self.anthropic else 'missing'})")

    __str__ = __repr__


@dataclass(frozen=True)
class Config:
    receiver: ReceiverConfig = field(default_factory=ReceiverConfig)
    link: LinkConfig = field(default_factory=LinkConfig)
    secrets: Secrets = field(default_factory=Secrets)


def check_host_port(value: str) -> str:
    if not isinstance(value, str) or not HOST_PORT.match(value):
        raise ConfigError(f"receiver must be host:port, got {value!r}")
    return value


def check_freq(value: float) -> float:
    try:
        khz = float(value)
    except (TypeError, ValueError):
        raise ConfigError(f"frequency must be a number in kHz, got {value!r}") from None
    if not FREQ_RANGE_KHZ[0] <= khz <= FREQ_RANGE_KHZ[1]:
        raise ConfigError(f"frequency must be {FREQ_RANGE_KHZ[0]:g}–{FREQ_RANGE_KHZ[1]:g} kHz, got {khz:g}")
    return khz


def _section(cls, values: dict, name: str):
    known = {f.name: f for f in fields(cls)}
    unknown = sorted(set(values) - set(known))
    if unknown:
        raise ConfigError(f"unknown key(s) in [{name}]: {', '.join(unknown)}")
    out = cls()
    for key, value in values.items():
        default = getattr(out, key)
        if isinstance(default, tuple):
            if not (isinstance(value, list) and len(value) == len(default)):
                raise ConfigError(f"[{name}] {key} must be a list of {len(default)} values")
            value = tuple(type(default[0])(v) for v in value)
        elif isinstance(default, float):
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ConfigError(f"[{name}] {key} must be a number")
            value = float(value)
        elif not isinstance(value, type(default)):
            raise ConfigError(f"[{name}] {key} must be {type(default).__name__}")
        out = replace(out, **{key: value})
    return out


def parse_env(text: str) -> dict[str, str]:
    """KEY=VALUE lines; quotes and trailing ` #` comments stripped; blank and comment lines skipped."""
    env = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value[:1] in ("'", '"'):
            value = value[1:].split(value[0], 1)[0]
        else:
            value = value.split(" #", 1)[0].split("\t#", 1)[0].strip()
        env[key.strip()] = value
    return env


def load_config(toml_path: pathlib.Path | None = None, env_path: pathlib.Path | None = None) -> Config:
    """The configuration: defaults, then `sruti.toml` key by key, then the keys from `.env`.

    Missing files are fine: defaults apply and the keys are reported missing.
    """
    toml_path = toml_path or pathlib.Path("sruti.toml")
    env_path = env_path or pathlib.Path(".env")
    data = {}
    if toml_path.exists():
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"{toml_path}: {exc}") from None
    unknown = sorted(set(data) - {"receiver", "link"})
    if unknown:
        raise ConfigError(f"unknown section(s) in {toml_path}: {', '.join(unknown)}")
    receiver = _section(ReceiverConfig, data.get("receiver", {}), "receiver")
    check_host_port(receiver.host_port)
    check_freq(receiver.freq_khz)
    lo, hi = receiver.passband
    if not 0 <= lo < hi <= 6000:
        raise ConfigError("[receiver] passband must be [low, high] Hz with 0 <= low < high <= 6000")
    link = _section(LinkConfig, data.get("link", {}), "link")
    if not 0 < link.reconnect_initial_s <= link.reconnect_max_s:
        raise ConfigError("[link] needs 0 < reconnect_initial_s <= reconnect_max_s")
    env = parse_env(env_path.read_text(encoding="utf-8")) if env_path.exists() else {}
    secrets = Secrets(gemini=env.get("GEMINI_API_KEY", ""), anthropic=env.get("ANTHROPIC_API_KEY", ""))
    return Config(receiver=receiver, link=link, secrets=secrets)
