# 🌙 Moonphase

A small **macOS menu bar** app: moon phase, chart, and sky information side by side. It uses your location (with permission) for accurate rise/set and chart data.

**Source:** [github.com/guillermodoghel/moonphase](https://github.com/guillermodoghel/moonphase)

## ✨ What you get

- 🧭 **Menu bar** moon phase and astral/sky context  
- 📊 **Chart + info** in the popover, plus a larger **Astral chart** window  
- 🌍 **Location** for local rise/set (macOS will prompt for access)  
- ⚙️ **Settings… (⌘,)** — start at login via a personal Launch Agent, optional *KeepAlive* (service-style relaunch)  
- 🔐 **One menubar copy** at a time (lock file; safe when `launchctl` spawns a second process right after you enable login items)

## 📋 Requirements

- 🍎 **macOS** (AppKit / menu bar; not for Windows or Linux)  
- 🔧 [Git](https://git-scm.com/) and **Python 3.10+** (3.12+ recommended) with `pip`  
  *Install Python from [python.org](https://www.python.org/downloads/) or Homebrew if you have no `python3`.*

## 🚀 One-line install

```bash
curl -fsSL "https://raw.githubusercontent.com/guillermodoghel/moonphase/main/setup.sh" | bash
```

The default clone URL is [guillermodoghel/moonphase](https://github.com/guillermodoghel/moonphase) (set `MOONPHASE_REPO` to use a fork or mirror). The script creates a venv, installs [requirements.txt](requirements.txt), and adds a `moonphase` command under `~/.local/bin` (or `MOONPHASE_BIN_DIR`). The repo must be cloneable without an interactive prompt (public, or stored credentials).

**Optional environment variables** (all optional; defaults shown):

| Variable | Default | Meaning |
|----------|---------|---------|
| `MOONPHASE_REPO` | `https://github.com/guillermodoghel/moonphase.git` | Git URL to clone |
| `MOONPHASE_INSTALL` | `$HOME/Applications/moonphase` | Where the clone and `.venv` live (ignored when you run `setup.sh` from a local checkout) |
| `MOONPHASE_BIN_DIR` | `~/.local/bin` | Where the `moonphase` launcher is written |

After install, if `moonphase` is not found, add that bin directory to your `PATH` (the installer prints a zsh `export` line you can copy).

## 📥 Install from a clone (your machine)

```bash
cd moonphase   # your git clone
./setup.sh
```

## 🛠️ Manual install (from a clone)

```bash
cd moonphase
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
python moonphase.py
```

## ▶️ Run

- `moonphase` (if `~/.local/bin` is on your `PATH`)  
- or `~/.local/bin/moonphase` / `path/to/venv/bin/python path/to/moonphase.py`  

The **wrapper** the installer creates points at the same venv and `moonphase.py` the app will record when you use **Settings → start at login**, so paths stay consistent.

## ⚙️ Settings: run at login

Open **Settings…** in the menubar (⌘,). There you can:

1. **Start at login** — installs a personal [Launch Agent](https://www.launchd.info/) in `~/Library/LaunchAgents` as `com.moonphase.menubar.plist` and loads it for your user with `launchctl`. No `.app` bundle required; the job points at the **current** `python` and this repo’s `moonphase.py` when you turn the option on. It also appears in **System Settings → General → Login Items** (or *Background* items on newer macOS).

2. **Keep it running (KeepAlive)** — optional. `launchd` can restart the process if it quits, closer to a classic *service* plist. Leave it off for a simple “start once at login”.

3. The app briefly switches to a normal **activation policy** while Settings (or the Astral chart window) is open so windows get focus; it returns to a pure menu bar style when you close the last of those windows.

If you use **another** Launch Agent (for example an older `com.moonphase.app` or custom plist) for the *same* code, disable one path so you do not run two copies. The installer and this README only describe the in-app, `com.moonphase.menubar` flow.

## ✏️ License

No `LICENSE` file in this repository yet; add one if you want to specify terms of use for others.
