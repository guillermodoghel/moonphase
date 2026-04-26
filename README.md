# Moonphase

A small **macOS menu bar** app: moon phase, chart, and sky information side by side. It uses your location (with permission) for accurate rise/set and chart data.

**Source:** [github.com/guillermodoghel/moonphase](https://github.com/guillermodoghel/moonphase)

## Requirements

- macOS (uses AppKit / menu bar; not supported on Windows or Linux)
- [Git](https://git-scm.com/) and **Python 3.10+** (3.12+ recommended) with `pip`  
  *Install Python from [python.org](https://www.python.org/downloads/) or Homebrew if your system has no `python3`.*

## One-line install

```bash
curl -fsSL "https://raw.githubusercontent.com/guillermodoghel/moonphase/main/setup.sh" | bash
```

The default clone URL is [guillermodoghel/moonphase](https://github.com/guillermodoghel/moonphase) (set `MOONPHASE_REPO` to use a fork or mirror). The script creates a venv, installs [requirements.txt](requirements.txt), and places a `moonphase` command in `~/.local/bin` (you can change paths with the table below). The repository must be cloneable without interactive login (a public URL, or credentials you have already stored for Git).

**Optional environment variables** (all optional; defaults shown):

| Variable | Default | Meaning |
|----------|---------|---------|
| `MOONPHASE_REPO` | `https://github.com/guillermodoghel/moonphase.git` | Git URL to clone |
| `MOONPHASE_INSTALL` | `$HOME/Applications/moonphase` | Where the clone and `.venv` live (ignored when you run `setup.sh` from a local checkout) |
| `MOONPHASE_BIN_DIR` | `$HOME/.local/bin` | Where the `moonphase` launcher is written |

After install, if `moonphase` is not found, add `~/.local/bin` to your `PATH` (the installer prints the exact `export` line for zsh).

## Install from a clone (same machine)

```bash
cd moonphase   # your git clone
./setup.sh
```

## Manual install (from a clone)

```bash
cd moonphase
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
python moonphase.py
```

## Run

- With installer: `moonphase` (after `PATH` includes `~/.local/bin` if needed), or `~/.local/bin/moonphase`
- From a venv: `python moonphase.py`

Grant **Location** when macOS asks so the app can compute local sky and chart data.

## License

No `LICENSE` file in this repository yet; add one if you want to specify terms of use for others.
