#!/usr/bin/env python3
"""One-step bootstrap for jtop-installer (no uv, pip, or git required).

Usage:
    curl -LsSf https://raw.githubusercontent.com/whitesscott/jtop_installer/main/bootstrap.py | python3 - install
    curl -LsSf https://raw.githubusercontent.com/whitesscott/jtop_installer/main/bootstrap.py | python3 - upgrade

Downloads this repo's source tarball from GitHub, imports the jtop_installer
package from a temporary directory, and runs the CLI — which then bootstraps
uv itself if needed. Only the Python standard library is used; nothing is
installed on the system by this script.

Environment overrides:
    JTOP_INSTALLER_REPO    GitHub "owner/repo" (default: whitesscott/jtop_installer)
    JTOP_INSTALLER_BRANCH  branch to fetch (default: main)
"""
import io
import os
import sys
import tarfile
import tempfile
import urllib.request

REPO = os.environ.get("JTOP_INSTALLER_REPO", "whitesscott/jtop_installer")
BRANCH = os.environ.get("JTOP_INSTALLER_BRANCH", "main")
TARBALL_URL = "https://github.com/{repo}/archive/refs/heads/{branch}.tar.gz"


def package_from_github(tmp, url):
    """Extract the jtop_installer package from a repo tarball into tmp."""
    print("Fetching {}".format(url))
    with urllib.request.urlopen(url, timeout=60) as response:
        buffer = io.BytesIO(response.read())
    extracted = False
    with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            parts = member.name.split("/")
            # Works for both layouts:
            #   jtop_installer-<branch>/jtop_installer/*.py         (this repo)
            #   <repo>-<branch>/jtop_installer/jtop_installer/*.py  (monorepo)
            if "jtop_installer" not in parts or ".." in parts:
                continue
            last = len(parts) - 1 - parts[::-1].index("jtop_installer")
            rel = "/".join(parts[last:])
            dest = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as out:
                out.write(tar.extractfile(member).read())
            extracted = True
    if not extracted:
        raise RuntimeError("jtop_installer package not found in {}".format(url))
    return tmp


def main():
    with tempfile.TemporaryDirectory() as tmp:
        url = TARBALL_URL.format(repo=REPO, branch=BRANCH)
        path = package_from_github(tmp, url)
        sys.path.insert(0, path)
        from jtop_installer.cli import main as cli_main
        return cli_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
