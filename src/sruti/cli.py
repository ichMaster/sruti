"""The command line: `sruti listen --receiver <host:port> --freq <kHz>` (ARCHITECTURE §Core and the desktop app)."""

import argparse
import sys

from sruti import __version__
from sruti.config import ConfigError, check_freq, check_host_port


def _host_port(value: str) -> str:
    try:
        return check_host_port(value)
    except ConfigError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _freq(value: str) -> float:
    try:
        return check_freq(value)
    except ConfigError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sruti", description="A private CW listening agent.")
    parser.add_argument("--version", action="version", version=f"sruti {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    listen = commands.add_parser("listen", help="listen to one receiver and frequency, headless")
    listen.add_argument("--receiver", type=_host_port, required=True, help="a public KiwiSDR, host:port")
    listen.add_argument("--freq", type=_freq, required=True, help="the signal's frequency in kHz (100–30000)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "listen":
        print(f"sruti listen {args.receiver} · {args.freq:g} kHz — the receiver link is not wired yet",
              file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
