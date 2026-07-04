import argparse
import os
import sys

from . import __version__
from .core import DEFAULT_PYTHON, DEFAULT_REF, InstallerError, auto, install, upgrade


def main(argv=None):
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    if not argv:
        argv = ["auto"]

    parser = argparse.ArgumentParser(
        prog="jtop-installer",
        description=(
            "Install or upgrade jetson-stats (jtop) into an isolated uv venv "
            "at ~/.local/share/jtop, with a /usr/local/bin/jtop symlink and a "
            "systemd service. Never writes to system site-packages. "
            "With no arguments, detects any existing jtop install and runs "
            "'upgrade' or 'install' accordingly."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_auto = subparsers.add_parser(
        "auto",
        help="Detect existing jtop and run install or upgrade accordingly (default).",
    )

    parser_install = subparsers.add_parser(
        "install", help="Create the jtop venv, symlink, and systemd service."
    )

    parser_upgrade = subparsers.add_parser(
        "upgrade",
        help="Upgrade jetson-stats in the existing venv (removes legacy system installs).",
    )

    for sub in (parser_auto, parser_install):
        sub.add_argument(
            "-p", "--python",
            default=DEFAULT_PYTHON,
            help="Python version for the venv (default: %(default)s).",
        )

    for sub in (parser_auto, parser_install, parser_upgrade):
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
        if args.command == "upgrade":
            return upgrade(ref=args.ref)
        return auto(ref=args.ref, python=args.python)
    except InstallerError as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
