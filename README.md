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

## Settings: run at login

Open **Settings…** from the menu bar (⌘,). There you can:

1. **Start at login** — install a *personal* [Launch Agent](https://www.launchd.info/) in `~/Library/LaunchAgents` as `com.moonphase.menubar.plist`, loaded with `launchctl` for your user. This is a good match for a script-based app: no `.app` bundle, and it shows up in **System Settings → General → Login Items** (or Background Items on newer macOS) alongside other login items. The agent runs the *same* `python` and `moonphase.py` you are using (paths are written when you turn the option on).

2. **Keep it running (KeepAlive)** — optional. If you turn this on, `launchd` will restart the process if it crashes or exits, closer to a traditional `launchd` *service* (like a manual `KeepAlive` in a plist). Leave it off for a simple “start once at login” behavior.

Only one copy of the app should be in the menubar: a file lock in `/tmp` makes a second process exit immediately (for example, right after the agent is installed, when `launchctl` may start another instance). If you previously set up a **separate** Launch Agent (for example a hand-edited `com.moonphase.app` plist) that points at the same app, turn one of them off so you do not fight two start paths.

## License

No `LICENSE` file in this repository yet; add one if you want to specify terms of use for others.
