# jtop-installer

Bootstrap installer for [jetson-stats](https://github.com/rbonghi/jetson_stats) (`jtop`).

It installs jtop into an **isolated uv venv** at `~/.local/share/jtop` — never
into system site-packages — so it works on externally managed Pythons without
`--break-system-packages`. System-wide it only creates:

- a symlink: `/usr/local/bin/jtop` → `~/.local/share/jtop/bin/jtop`
- a systemd unit: `/etc/systemd/system/jtop.service`

This is a pure-Python replacement for the former
`install_jtop_torun_without_sudo.sh` and `upgrade-jtop.sh` scripts.

## Usage

Run as a **regular user** (not with sudo — it invokes sudo itself when needed;
run `sudo -v` first if you prefer to prime credentials).

### One step, no prerequisites (only python3)

```bash
curl -LsSf https://raw.githubusercontent.com/whitesscott/jtop_installer/main/bootstrap.py | python3 -
```

With no arguments it auto-detects: if jtop already exists (venv, symlink,
`PATH`, or a legacy copy in system/user site-packages or /opt) it runs
`upgrade`, otherwise `install`. Append `install` or `upgrade` to force one:

```bash
curl -LsSf https://raw.githubusercontent.com/whitesscott/jtop_installer/main/bootstrap.py | python3 - install
```

`bootstrap.py` downloads this repo's source tarball from GitHub, imports the
package from a temporary directory, and runs the CLI — which then bootstraps
uv itself if needed. Nothing is installed on the system by the bootstrap
itself. Set `JTOP_INSTALLER_BRANCH` to bootstrap from a branch other than
`main`, or `JTOP_INSTALLER_REPO` to use a fork.

### With uv or pipx already installed

With [uv](https://docs.astral.sh/uv/) installed:

```bash
# Auto-detect (upgrade if jtop exists, install otherwise)
uvx jtop-installer

# Fresh install
uvx jtop-installer install

# Upgrade (also removes any legacy system-wide jtop installs)
uvx jtop-installer upgrade
```

Or with pipx:

```bash
pipx run jtop-installer install
```

On a machine without uv/pipx, run it straight from the repo with system Python
(stdlib only, no dependencies):

```bash
python3 -m jtop_installer.cli install
```

(from this directory; `install` will bootstrap uv itself if it is missing.)

### Options

- `--ref REQUIREMENT` — what to install, e.g. `jetson-stats` (PyPI) or a git
  URL/branch. Defaults to `git+https://github.com/rbonghi/jetson_stats.git`.
  Also settable via the `JTOP_REF` environment variable.
- `install -p / --python VERSION` — Python version for the venv (default `3.12`;
  uv downloads it if not present).

## What `install` does

1. Bootstraps `uv` if missing (downloads the official installer via stdlib urllib).
2. Ensures the `jtop` group exists.
3. Creates the venv at `~/.local/share/jtop` (`uv venv -p 3.12 --seed`).
4. Installs/upgrades jetson-stats into it.
5. Optionally symlinks NVIDIA's proprietary `pylibjetsonpower` (Thor) from
   system dist-packages into the venv, if present.
6. Creates the `/usr/local/bin/jtop` symlink and the `jtop.service` systemd
   unit, then enables and starts the service.

## What `upgrade` does

1. Removes legacy system-wide jtop installs (pip uninstall from every system
   Python, then force-removes leftovers) — the venv is untouched by this step.
2. Falls back to a full `install` if uv or the venv is missing/broken.
3. Stops the service, clears root-owned `__pycache__` dirs in the venv,
   force-reinstalls jetson-stats, refreshes the symlink, restarts the service.

## Building / publishing

```bash
uv build          # produces dist/*.whl and dist/*.tar.gz
uv publish        # upload to PyPI (requires credentials)
```
