#!/usr/bin/env python3
"""One-step bootstrap for jtop-installer (no uv, pip, or git required).

Usage:
    curl -LsSf https://raw.githubusercontent.com/rbonghi/jetson_stats/master/jtop_installer/bootstrap.py | python3 - install
    curl -LsSf .../bootstrap.py | python3 - upgrade

Downloads the jtop-installer wheel from PyPI (or, if not published there,
the repo tarball from GitHub), imports it from a temporary directory, and
runs the CLI. Only the Python standard library is used.
"""
import io
import json
import os
import sys
import tarfile
import tempfile
import urllib.request

PYPI_JSON_URL = "https://pypi.org/pypi/jtop-installer/json"
REPO_TARBALL_URL = "https://github.com/rbonghi/jetson_stats/archive/refs/heads/{branch}.tar.gz"
BRANCH = os.environ.get("JTOP_INSTALLER_BRANCH", "master")


def wheel_from_pypi(tmp):
    """Download the latest jtop-installer wheel from PyPI; None if unavailable."""
    try:
        with urllib.request.urlopen(PYPI_JSON_URL, timeout=15) as response:
            data = json.load(response)
        for release_file in data.get("urls", []):
            if release_file.get("packagetype") == "bdist_wheel":
                dest = os.path.join(tmp, release_file["filename"])
                print("Downloading {}".format(release_file["url"]))
                urllib.request.urlretrieve(release_file["url"], dest)
                return dest
    except Exception as error:
        print("PyPI not usable ({}); falling back to GitHub.".format(error))
    return None


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
            # <repo>-<branch>/jtop_installer/jtop_installer/*.py
            if parts.count("jtop_installer") < 2 or ".." in parts:
                continue
            rel = "/".join(parts[parts.index("jtop_installer") + 1:])
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
        path = wheel_from_pypi(tmp)
        if path is None:
            path = package_from_github(tmp, REPO_TARBALL_URL.format(branch=BRANCH))
        sys.path.insert(0, path)
        from jtop_installer.cli import main as cli_main
        return cli_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
