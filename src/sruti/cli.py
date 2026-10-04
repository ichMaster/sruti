"""The command line: `sruti listen --receiver <host:port> --freq <kHz>` (ARCHITECTURE §Core and the desktop app)."""

import argparse
import asyncio
import dataclasses
import pathlib
import sys

from sruti import __version__
from sruti.config import ConfigError, check_freq, check_host_port, load_config


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
    listen.add_argument("--record", type=pathlib.Path, metavar="DIR",
                        help="record the session as WAV + capture into DIR")
    listen.add_argument("--raw", action="store_true", help="print every raw message to and from the receiver")
    listen.add_argument("--drop-after", type=float, help=argparse.SUPPRESS)  # live reconnect check
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "listen":
        from sruti.listen import listen
        from sruti.receiver.transport import connect_kiwisdr

        try:
            config = load_config()
        except ConfigError as exc:
            print(f"sruti: {exc}", file=sys.stderr)
            return 2
        receiver = dataclasses.replace(config.receiver, host_port=args.receiver, freq_khz=args.freq)
        final = asyncio.run(listen(config, receiver, connect_kiwisdr, record_dir=args.record, raw=args.raw,
                                   drop_after=args.drop_after))
        return 0 if final in ("stopped", "ended") else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
