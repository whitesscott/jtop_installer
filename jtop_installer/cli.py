import argparse
import os
import sys

from . import __version__
from .core import DEFAULT_PYTHON, DEFAULT_REF, InstallerError, install, upgrade


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="jtop-installer",
        description=(
            "Install or upgrade jetson-stats (jtop) into an isolated uv venv "
            "at ~/.local/share/jtop, with a /usr/local/bin/jtop symlink and a "
            "systemd service. Never writes to system site-packages."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_install = subparsers.add_parser(
        "install", help="Create the jtop venv, symlink, and systemd service."
    )
    parser_install.add_argument(
        "-p", "--python",
        default=DEFAULT_PYTHON,
        help="Python version for the venv (default: %(default)s).",
    )

    parser_upgrade = subparsers.add_parser(
        "upgrade",
        help="Upgrade jetson-stats in the existing venv (removes legacy system installs).",
    )

    for sub in (parser_install, parser_upgrade):
        sub.add_argument(
            "--ref",
            default=os.environ.get("JTOP_REF", DEFAULT_REF),
            help=(
                "pip requirement to install, e.g. 'jetson-stats' or a git URL. "
                "Also settable via the JTOP_REF environment variable "
                "(default: %(default)s)."
            ),
        )

    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            return install(ref=args.ref, python=args.python)
        return upgrade(ref=args.ref)
    except InstallerError as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
