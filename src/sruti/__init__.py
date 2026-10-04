"""sruti — a private listening agent: CW from a public KiwiSDR, decoded and explained on the Mac."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sruti")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0+unknown"
