"""Install/upgrade jetson-stats (jtop) into an isolated uv venv.

The venv lives in the user's home directory; only a symlink and a systemd
unit are placed system-wide (via sudo). System site-packages are never
written to, so there is no need for --break-system-packages.
"""
import glob
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

APP_NAME = "jtop"
PKG_NAME = "jetson_stats"
VENV_DIR = Path.home() / ".local" / "share" / APP_NAME
JTOP_BIN = VENV_DIR / "bin" / APP_NAME
JTOP_PYTHON = VENV_DIR / "bin" / "python"
SYMLINK_PATH = Path("/usr/local/bin") / APP_NAME
SYSTEMD_SERVICE = APP_NAME + ".service"
SYSTEMD_UNIT = Path("/etc/systemd/system") / SYSTEMD_SERVICE
DEFAULT_REF = "git+https://github.com/rbonghi/jetson_stats.git"
DEFAULT_PYTHON = "3.12"
UV_INSTALL_URL = "https://astral.sh/uv/install.sh"

SYSTEMD_UNIT_CONTENT = """\
[Unit]
Description=Jetson Stats (jtop service)
After=network.target

[Service]
Environment="JTOP_SERVICE=True"
ExecStart={exec_start} --force
Restart=on-failure
RestartSec=10s
TimeoutStartSec=30s
TimeoutStopSec=30s

[Install]
WantedBy=multi-user.target
"""


class InstallerError(Exception):
    pass


def run(cmd, sudo=False, check=True, capture=False, input_bytes=None):
    cmd = [str(c) for c in cmd]
    if sudo:
        cmd = ["sudo"] + cmd
    result = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE if capture else None,
        input=input_bytes,
    )
    if check and result.returncode != 0:
        raise InstallerError(
            "command failed with exit code {}: {}".format(result.returncode, " ".join(cmd))
        )
    return result.stdout.decode() if capture else ""


def ensure_not_root():
    if os.geteuid() == 0:
        raise InstallerError(
            "Run this command as a regular user, NOT with sudo.\n"
            "It will invoke sudo itself where needed (run 'sudo -v' first if you prefer)."
        )


def uv_path():
    found = shutil.which("uv")
    if found:
        return found
    for candidate in (Path.home() / ".local" / "bin" / "uv", Path.home() / ".cargo" / "bin" / "uv"):
        if candidate.is_file() and os.access(str(candidate), os.X_OK):
            return str(candidate)
    return None


def uv_self_update(uv):
    # Fails harmlessly when uv is not managed by the standalone installer
    # (e.g. installed via pip or apt), so don't abort on error.
    print("Updating 'uv'...")
    run([uv, "self", "update", "-q"], check=False)


def ensure_uv():
    uv = uv_path()
    if uv:
        print("'uv' is already installed.")
        uv_self_update(uv)
        return uv
    print("Installing 'uv' (an exceptionally fast Python package installer)...")
    with urllib.request.urlopen(UV_INSTALL_URL) as response:
        script = response.read()
    run(["sh"], input_bytes=script)
    uv = uv_path()
    if not uv:
        raise InstallerError("uv installation failed: 'uv' not found after install.")
    return uv


def jtop_service_exists():
    out = run(
        ["systemctl", "list-unit-files", SYSTEMD_SERVICE, "--no-legend"],
        capture=True,
        check=False,
    )
    return any(line.startswith(SYSTEMD_SERVICE) for line in out.splitlines())


def link_pylibjetsonpower():
    """Make proprietary pylibjetsonpower visible inside the venv (Thor).

    Not required for upstream jetson_stats; a local convenience so the
    service (running from this venv) can import pylibjetsonpower if present.
    """
    print("Checking for NVIDIA pylibjetsonpower (optional)...")
    patterns = [
        "/usr/lib/python3/dist-packages/pylibjetsonpower",
        "/usr/local/lib/python*/dist-packages/pylibjetsonpower",
        "/usr/lib/python*/dist-packages/pylibjetsonpower",
    ]
    source = None
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if os.path.isfile(os.path.join(path, "__init__.py")):
                source = path
                break
        if source:
            break
    if not source:
        print("  pylibjetsonpower not found (skipping).")
        return
    purelib = run(
        [JTOP_PYTHON, "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        capture=True,
    ).strip()
    dest = Path(purelib) / "pylibjetsonpower"
    print("  Found: {}".format(source))
    print("  Linking into venv: {}".format(dest))
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.is_dir():
        shutil.rmtree(str(dest))
    dest.symlink_to(source)


def write_systemd_unit():
    content = SYSTEMD_UNIT_CONTENT.format(exec_start=SYMLINK_PATH)
    run(["tee", SYSTEMD_UNIT], sudo=True, capture=True, input_bytes=content.encode())


def _find_system_dirs(name):
    out = run(
        [
            "find", "/usr/lib", "/usr/local/lib",
            "-type", "d",
            "-name", name,
            "-path", "*/python3*/*-packages/*",
            "-prune", "-print",
        ],
        sudo=True,
        capture=True,
        check=False,
    )
    venv_prefix = str(VENV_DIR) + os.sep
    return [line for line in out.splitlines() if line and not line.startswith(venv_prefix)]


def remove_legacy_jtop():
    """Remove legacy system-wide jtop installs outside the uv venv."""
    print("Checking for legacy system jtop installs outside the uv venv...")
    legacy_dirs = _find_system_dirs(APP_NAME)
    if not legacy_dirs:
        print("No legacy jtop installs found.")
        return

    print("Found legacy jtop directories:")
    for path in legacy_dirs:
        print("  {}".format(path))

    print("Attempting to uninstall legacy system jtop with system Python tools...")
    pythons = sorted(
        set(
            glob.glob("/usr/bin/python3")
            + glob.glob("/usr/bin/python3.[0-9]*")
            + glob.glob("/usr/local/bin/python3")
            + glob.glob("/usr/local/bin/python3.[0-9]*")
        )
    )
    for py in pythons:
        if not os.access(py, os.X_OK):
            continue
        print("Trying: sudo {} -m pip uninstall -y jetson-stats jetson_stats".format(py))
        result = subprocess.run(
            ["sudo", py, "-m", "pip", "uninstall", "-y", "jetson-stats", "jetson_stats"]
        )
        if result.returncode != 0:
            print("Retrying with --break-system-packages for externally managed Python...")
            subprocess.run(
                ["sudo", py, "-m", "pip", "uninstall", "-y", "--break-system-packages",
                 "jetson-stats", "jetson_stats"]
            )

    print("Rechecking for leftover legacy jtop directories...")
    leftover_dirs = _find_system_dirs(APP_NAME)
    if leftover_dirs:
        print("Force-removing leftover directories:")
        for path in leftover_dirs:
            print("  {}".format(path))
        run(["rm", "-rf"] + leftover_dirs, sudo=True)
    else:
        print("All legacy jtop directories removed.")

    dist_info_dirs = _find_system_dirs("jetson_stats-*.dist-info")
    if dist_info_dirs:
        print("Removing leftover dist-info directories:")
        for path in dist_info_dirs:
            print("  {}".format(path))
        run(["rm", "-rf"] + dist_info_dirs, sudo=True)


def install(ref=DEFAULT_REF, python=DEFAULT_PYTHON):
    ensure_not_root()
    run(["sudo", "-v"])

    uv = ensure_uv()

    # To be safe let's make sure group jtop exists.
    run(["groupadd", "-f", APP_NAME], sudo=True)

    print("Creating Python virtual environment in {}...".format(VENV_DIR))
    run([uv, "venv", VENV_DIR, "-p", python, "--seed"])

    print("Installing/upgrading {} from: {}".format(PKG_NAME, ref))
    run([uv, "pip", "install", "--python", JTOP_PYTHON, "--upgrade", ref])

    link_pylibjetsonpower()

    if not os.access(str(JTOP_BIN), os.X_OK):
        raise InstallerError("Installation failed: '{}' binary not found.".format(JTOP_BIN))

    # This makes 'jtop' (user) and 'sudo jtop' (root) work correctly.
    run(["ln", "-sf", JTOP_BIN, SYMLINK_PATH], sudo=True)
    print("Symlink created: {}".format(SYMLINK_PATH))

    if SYSTEMD_UNIT.exists():
        print("Found existing jtop service. It will be overwritten.")
    print("Creating systemd service: {}".format(SYSTEMD_UNIT))
    write_systemd_unit()

    print("Enabling and starting {} system service".format(APP_NAME))
    run(["systemctl", "daemon-reload"], sudo=True)
    run(["systemctl", "enable", SYSTEMD_SERVICE], sudo=True)
    run(["systemctl", "restart", SYSTEMD_SERVICE], sudo=True)
    run(["systemctl", "status", SYSTEMD_SERVICE, "--no-pager"], sudo=True, check=False)

    print()
    print("Installation complete!")
    print()
    print("You can now run '{0}' or 'sudo {0}' (privileged).".format(APP_NAME))
    return 0


def upgrade(ref=DEFAULT_REF):
    ensure_not_root()
    run(["sudo", "-v"])

    remove_legacy_jtop()

    uv = uv_path()
    if uv is None or not VENV_DIR.is_dir():
        print("uv or jtop venv not found — running full installer...")
        return install(ref=ref)

    if not os.access(str(JTOP_PYTHON), os.X_OK):
        print("Broken jtop venv (Python not found): {}".format(JTOP_PYTHON))
        print("Removing and re-running full installer...")
        run(["rm", "-rf", VENV_DIR], sudo=True)
        return install(ref=ref)

    uv_self_update(uv)

    if jtop_service_exists():
        print("Stopping {} before upgrade...".format(SYSTEMD_SERVICE))
        run(["systemctl", "stop", SYSTEMD_SERVICE], sudo=True, check=False)
    else:
        print("{} not found; continuing without stopping service.".format(SYSTEMD_SERVICE))

    # The service runs as root, so __pycache__ inside the venv may be root-owned.
    print("Removing stale __pycache__ directories in {}...".format(VENV_DIR))
    run(
        ["find", VENV_DIR, "-type", "d", "-name", "__pycache__", "-prune",
         "-exec", "rm", "-rf", "--", "{}", "+"],
        sudo=True,
        check=False,
    )

    print("Upgrading {} from:".format(PKG_NAME))
    print("  {}".format(ref))
    run([uv, "pip", "install", "--python", JTOP_PYTHON, "--upgrade", "--force-reinstall", ref])

    if not os.access(str(JTOP_BIN), os.X_OK):
        raise InstallerError("Upgrade failed: jtop binary not found: {}".format(JTOP_BIN))

    print("Refreshing symlink:")
    print("  {} -> {}".format(SYMLINK_PATH, JTOP_BIN))
    run(["ln", "-sf", JTOP_BIN, SYMLINK_PATH], sudo=True)

    if jtop_service_exists():
        print("Reloading systemd and restarting {}...".format(SYSTEMD_SERVICE))
        run(["systemctl", "daemon-reload"], sudo=True, check=False)
        result = subprocess.run(["sudo", "systemctl", "restart", SYSTEMD_SERVICE])
        if result.returncode != 0:
            print("WARNING: upgraded jtop, but failed to restart {}.".format(SYSTEMD_SERVICE))
            print("You can try manually with: sudo systemctl restart {}".format(SYSTEMD_SERVICE))
    else:
        print("{} not found; skipping systemd reload/restart.".format(SYSTEMD_SERVICE))

    print()
    print("Upgrade complete.")
    print("jtop executable: {} -> {}".format(SYMLINK_PATH, JTOP_BIN))
    run([JTOP_BIN, "--version"], check=False)
    return 0
