# jtop-installer

`jtop-installer` installs or upgrades [`jetson-stats`](https://github.com/rbonghi/jetson_stats), which provides the `jtop` program for NVIDIA Jetson systems.


## Installation

On a machine without `uv` or `pipx`, run direct from the repository using system Python to install `jtop`:

```bash
curl -LsSf https://raw.githubusercontent.com/whitesscott/jtop_installer/main/bootstrap.py | python3 -
```

## Using uv or pipx

If [`uv`](https://docs.astral.sh/uv/) is already installed:

```bash
uvx jtop-installer
```

If sudo apt install `pipx` is already installed:

```bash
pipx run jtop-installer
```

## What this package does

`jtop-installer` installs or upgrades Current Release `jetson-stats` / `jtop` into a `uv` virtual environment located at:

```text
~/.local/share/jtop
```

The installer uses the exceptionally fast `uv` virtual environment. It does not install `jetson-stats` into system site-packages. Instead, it avoids modifying Ubuntu/JetPack’s apt managed system Python that includes externally managed Python installations where `pip` enforces PEP 668 protections. It does not require `--break-system-packages`.

System-wide it only creates:
* a symlink:
  ```text
  /usr/local/bin/jtop -> ~/.local/share/jtop/bin/jtop
  ```
* a systemd service unit:
  ```text
  /etc/systemd/system/jtop.service
  ```

## Fresh installation

If `jetson-stats` / `jtop` has never been installed, this package performs a fresh installation of the current `jetson-stats` release from source.

The installer:

1. Bootstraps `uv` if it is missing by downloading the official installer using Python standard-library `urllib`.
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

