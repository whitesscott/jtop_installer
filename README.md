# jtop-installer

`jtop-installer` installs or upgrades [`jetson-stats`](https://github.com/rbonghi/jetson_stats), which provides the `jtop` program for NVIDIA Jetson systems.

## Installation

Choose **one** of the following installation commands:

**uv**

```bash
uvx jtop-installer
```

**pipx**

```bash
pipx run jtop-installer
```

**curl**

```bash
curl -LsSf https://raw.githubusercontent.com/whitesscott/jtop_installer/main/bootstrap.py | python3 -
```

> **Note:** The `curl` method uses the system Python as the installer.

## What this package does

`jtop-installer` installs or upgrades to the current release of `jetson-stats` / `jtop` in a `uv` virtual environment located at:

```text
~/.local/share/jtop
```

The installer creates a fast, isolated `uv` virtual environment for `jetson-stats`. It does not modify Ubuntu's system Python environment, respecting the PEP 668 protections that prevent `pip` from conflicting with the apt system package manager. It never requires `--break-system-packages`.

Installation runs as your normal user. A single `sudo` prompt covers the system-level actions: removing root-owned `__pycache__` directories created by `sudo jtop`, creating the `jtop` symlink, installing the systemd `jtop.service` unit, and creating the `jtop` group. Everything else — the virtual environment and `jetson-stats` itself — is installed in your home directory without root.


## Fresh installation

If `jetson-stats` / `jtop` has never been installed, this package performs a fresh installation of the current `jetson-stats` release from source.

The installer:

1. Bootstraps `uv` if it is missing by downloading the official installer using the Python standard-library `urllib`.
2. Ensures that the `jtop` group exists.
3. Creates the virtual environment at `~/.local/share/jtop`.
4. Installs `jetson-stats` into that virtual environment.
5. Creates the `/usr/local/bin/jtop` symlink so that `sudo jtop` works.
6. Creates the systemd `jtop.service` unit.
7. Enables and starts the `jtop` service.


## Upgrade

If `jetson-stats` / `jtop` was previously installed, this package upgrades it to the current `jetson-stats` release.

The installer:

1. Removes outdated legacy system-wide `jtop` installs by running `pip uninstall` from every detected system Python directory, then removing leftover files.
2. Leaves the isolated virtual environment untouched during legacy cleanup.
3. Falls back to a full installation if `uv` or the virtual environment is missing or broken.
4. Stops the `jtop` service.
5. Removes root-owned `__pycache__` directories from the virtual environment.
6. Reinstalls `jetson-stats`.
7. Refreshes the `/usr/local/bin/jtop` symlink.
8. Restarts the `jtop` service.
