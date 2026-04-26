#!/usr/bin/env bash
# Moonphase macOS install — can be run locally or: curl -fsSL … | bash
set -euo pipefail

REPO_URL="${MOONPHASE_REPO:-https://github.com/guillermodoghel/moonphase.git}"
INSTALL_DIR="${MOONPHASE_INSTALL:-$HOME/Applications/moonphase}"
BIN_STEM="${MOONPHASE_BIN_DIR:-$HOME/.local/bin}"
MAIN_PY="moonphase.py"
WRAPPER_NAME="moonphase"

die() { echo "moonphase install: $*" >&2; exit 1; }

if [[ "$(uname -s)" != "Darwin" ]]; then
  die "This app is macOS-only (it uses the menu bar and AppKit)."
fi
command -v python3 >/dev/null 2>&1 || die "python3 not found. Install from https://www.python.org/ or use Homebrew."

# If setup.sh is a real file next to the app, install from that tree (skip git)
USE_LOCAL=0
if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  _here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$_here/$MAIN_PY" && -f "$_here/requirements.txt" ]]; then
    INSTALL_DIR="$_here"
    USE_LOCAL=1
    echo "Installing from working tree: $INSTALL_DIR"
  fi
fi
if [[ "$USE_LOCAL" -ne 1 ]]; then
  command -v git >/dev/null 2>&1 || die "git is required. Install Xcode Command Line Tools: xcode-select --install"
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo "Updating existing clone in $INSTALL_DIR"
    git -C "$INSTALL_DIR" pull --ff-only
  elif [[ -d "$INSTALL_DIR" ]]; then
    die "Directory $INSTALL_DIR exists and is not a git clone. Set MOONPHASE_INSTALL to another path or remove the directory."
  else
    echo "Cloning $REPO_URL → $INSTALL_DIR"
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
  fi
fi

[[ -f "$INSTALL_DIR/$MAIN_PY" ]] || die "Expected $MAIN_PY in $INSTALL_DIR. Check REPO_URL and branch."

VENV_DIR="$INSTALL_DIR/.venv"
echo "Python venv → $VENV_DIR"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
python -m pip install -q -U pip
python -m pip install -q -r "$INSTALL_DIR/requirements.txt"

# Optional legacy LaunchAgent plist: paths for *this* machine only (any user’s INSTALL_DIR)
REAL_ROOT="$(cd "$INSTALL_DIR" && pwd)"
if [[ -f "$INSTALL_DIR/com.moonphase.app.plist.in" ]]; then
  R="$REAL_ROOT" VPY="$VENV_DIR/bin/python" MPY="$REAL_ROOT/$MAIN_PY" \
    "$VENV_DIR/bin/python" -c "import os, pathlib
r = pathlib.Path(os.environ['R'])
p = r / 'com.moonphase.app.plist.in'
t = p.read_text()
t = t.replace('@VENV_PYTHON@', os.environ['VPY'])
t = t.replace('@MOONPHASE_MAIN@', os.environ['MPY'])
out = r / 'com.moonphase.app.plist'
out.write_text(t)
print('Wrote', out)" || die "Failed to write com.moonphase.app.plist"
  echo
  echo "Wrote  $INSTALL_DIR/com.moonphase.app.plist  (from .plist.in) — optional *service* style"
  echo "  (KeepAlive). The menubar app uses Settings (⌘,) → com.moonphase.menubar; do not load"
  echo "  both. To use this one:  launchctl bootstrap \"gui/\$(id -u)\" \"$INSTALL_DIR/com.moonphase.app.plist\""
fi

mkdir -p "$BIN_STEM"
WRAPPER_PATH="$BIN_STEM/$WRAPPER_NAME"
cat > "$WRAPPER_PATH" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$INSTALL_DIR/$MAIN_PY" "\$@"
EOF
chmod +x "$WRAPPER_PATH"

AUTO_START="${MOONPHASE_AUTO_START:-1}"
if [[ "$AUTO_START" == "1" ]]; then
  if command -v pgrep >/dev/null 2>&1 && pgrep -f "$INSTALL_DIR/$MAIN_PY" >/dev/null 2>&1; then
    echo "Moonphase already running; skipping auto-start."
  else
    nohup "$VENV_DIR/bin/python" "$INSTALL_DIR/$MAIN_PY" \
      >/tmp/moonphase.log 2>/tmp/moonphase.err </dev/null &
    sleep 1
    if command -v pgrep >/dev/null 2>&1 && pgrep -f "$INSTALL_DIR/$MAIN_PY" >/dev/null 2>&1; then
      echo "Started Moonphase now (menu bar icon should appear)."
    else
      echo "Could not confirm startup automatically; run '$WRAPPER_NAME' manually."
    fi
  fi
fi

echo
echo "Installed. Run:  $WRAPPER_NAME"
echo "  (or:  $VENV_DIR/bin/python $INSTALL_DIR/$MAIN_PY)"
if [[ ":$PATH:" != *":$BIN_STEM:"* ]]; then
  echo
  echo "Add this to your shell config (~/.zshrc) so 'moonphase' is on your PATH:"
  echo "  export PATH=\"$BIN_STEM:\$PATH\""
fi
echo
echo "Location: macOS may ask for access so charts use your place on Earth."
echo "Start at login: menubar menu → Settings… (⌘,) and turn on the switch. That writes a"
echo "  Launch Agent for the same python + moonphase.py you just installed (System Settings"
echo "  → General → Login Items). If you also use another launchd job for this app, turn one off"
echo "  so only one process runs in the menubar."
