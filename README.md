# Moonphase

A small **macOS menu bar** app: moon phase, chart, and sky information side by side. It uses your location (with permission) for accurate rise/set and chart data.

## Requirements

- macOS (uses AppKit / menu bar; not supported on Windows or Linux)
- [Git](https://git-scm.com/) and **Python 3.10+** (3.12+ recommended) with `pip`  
  *Install Python from [python.org](https://www.python.org/downloads/) or Homebrew if your system has no `python3`.*

## One-line install

Push this repository to GitHub (or use another public `git` URL), then run (replace `YOUR_USER` and `main` if your branch is different):

```bash
export MOONPHASE_REPO="https://github.com/YOUR_USER/moonphase.git"   # optional; matches default in setup.sh if you use guillermodoghel/moonphase
curl -fsSL "https://raw.githubusercontent.com/YOUR_USER/moonphase/main/setup.sh" | bash
```

The script clones the repo, creates a venv, installs [requirements.txt](requirements.txt), and places a `moonphase` command in `~/.local/bin` (see table below to change paths). It only works if the `MOONPHASE_REPO` is cloneable (public, or you have git credentials for it).

**Optional environment variables** (all optional; defaults shown):

| Variable | Default | Meaning |
|----------|---------|---------|
| `MOONPHASE_REPO` | see `setup.sh` | Git URL to clone |
| `MOONPHASE_INSTALL` | `$HOME/Applications/moonphase` | Where the repo and `.venv` live |
| `MOONPHASE_BIN_DIR` | `$HOME/.local/bin` | Where the `moonphase` launcher is written |

After install, if `moonphase` is not found, add `~/.local/bin` to your `PATH` (the installer prints the exact `export` line for zsh).

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

- From install: `moonphase` (after `PATH` includes `~/.local/bin` if needed), or:  
  `~/.local/bin/moonphase`
- From a dev venv: `python moonphase.py`

Grant **Location** when macOS asks so the app can compute local sky and chart data.

## Publishing checklist

1. Create a public GitHub repository and push this project (avoid committing a local `venv/`; keep `requirements.txt` in the repo).
2. Replace `YOUR_USER` in the README `curl` example with your GitHub username.
3. Edit the default `MOONPHASE_REPO` in `setup.sh` if you do not use `guillermodoghel/moonphase`.
4. Tag a release if you use GitHub releases; the `raw.githubusercontent.com/.../main/setup.sh` URL is enough for the curl installer.

## License

Add a `LICENSE` file when you choose a license for publication.
