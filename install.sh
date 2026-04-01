#!/usr/bin/env bash
# ============================================================
#  Jira Timesheet - Installer
#
#  Verwendung:
#    curl -fsSL https://raw.githubusercontent.com/michaelblaess/jira-timesheet/main/install.sh | bash
#
#  Klont das Repository, erstellt ein venv und installiert alle Dependencies.
#  Voraussetzung: Python 3.10+ muss installiert sein.
#
#  Installiert nach: ~/.jira-timesheet-app/
#  Erstellt Wrapper:  ~/.local/bin/jira-timesheet
# ============================================================

set -e

REPO="michaelblaess/jira-timesheet"
INSTALL_DIR="$HOME/.jira-timesheet-app"
BIN_DIR="$HOME/.local/bin"
WRAPPER="$BIN_DIR/jira-timesheet"

echo
echo "  +================================================+"
echo "  |   Jira Timesheet - Installer                    |"
echo "  +================================================+"
echo

# --- Python pruefen ---
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &> /dev/null; then
        ver=$("$cmd" --version 2>&1)
        minor=$(echo "$ver" | grep -oP 'Python 3\.(\d+)' | grep -oP '\d+$')
        if [ -n "$minor" ] && [ "$minor" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            echo "  [OK] $ver gefunden ($cmd)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "  [FEHLER] Python 3.10+ nicht gefunden!"
    echo "  Bitte installieren: https://python.org"
    exit 1
fi
echo

# --- Download-Tool pruefen ---
DOWNLOAD_CMD=""
if command -v curl &> /dev/null; then
    DOWNLOAD_CMD="curl"
elif command -v wget &> /dev/null; then
    DOWNLOAD_CMD="wget"
else
    echo "  [FEHLER] Weder curl noch wget gefunden!"
    exit 1
fi

# --- Neuestes Release ermitteln ---
echo "  Suche neuestes Release..."
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

if [ "$DOWNLOAD_CMD" = "curl" ]; then
    RELEASE_JSON=$(curl -fsSL "$API_URL" 2>/dev/null) || RELEASE_JSON=""
else
    RELEASE_JSON=$(wget -qO- "$API_URL" 2>/dev/null) || RELEASE_JSON=""
fi

if [ -n "$RELEASE_JSON" ]; then
    VERSION=$(echo "$RELEASE_JSON" | grep -o '"tag_name": *"[^"]*"' | head -1 | sed 's/.*: *"//' | sed 's/"//')
    ZIP_URL=$(echo "$RELEASE_JSON" | grep -o '"zipball_url": *"[^"]*"' | head -1 | sed 's/.*: *"//' | sed 's/"//')
    echo "  [OK] Release: $VERSION"
else
    echo "  [WARNUNG] Kein Release gefunden, verwende main-Branch"
    VERSION="main"
    ZIP_URL="https://github.com/${REPO}/archive/refs/heads/main.zip"
fi
echo

# --- Download ---
TMPDIR=$(mktemp -d)
TMPFILE="$TMPDIR/source.zip"

echo "  Lade Quellcode herunter..."
if [ "$DOWNLOAD_CMD" = "curl" ]; then
    curl -fSL --progress-bar -o "$TMPFILE" "$ZIP_URL"
else
    wget --show-progress -qO "$TMPFILE" "$ZIP_URL"
fi
echo "  [OK] Download abgeschlossen"
echo

# --- Entpacken ---
echo "  Entpacke nach: $INSTALL_DIR"

# venv sichern falls vorhanden
VENV_BACKUP=""
if [ -d "$INSTALL_DIR/.venv" ]; then
    VENV_BACKUP="$TMPDIR/venv-bak"
    mv "$INSTALL_DIR/.venv" "$VENV_BACKUP"
fi

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
unzip -q "$TMPFILE" -d "$TMPDIR"

# GitHub zipball hat Unterordner
SUBDIR=$(find "$TMPDIR" -maxdepth 1 -type d -name "${REPO##*/}-*" -o -name "michaelblaess-*" | head -1)
if [ -n "$SUBDIR" ]; then
    mv "$SUBDIR"/* "$INSTALL_DIR/" 2>/dev/null || true
    mv "$SUBDIR"/.* "$INSTALL_DIR/" 2>/dev/null || true
fi

# venv wiederherstellen
if [ -n "$VENV_BACKUP" ] && [ -d "$VENV_BACKUP" ]; then
    mv "$VENV_BACKUP" "$INSTALL_DIR/.venv"
fi

rm -rf "$TMPDIR"
echo "  [OK] Entpackt"
echo

# --- venv + Dependencies ---
VENV_PYTHON="$INSTALL_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "  Erstelle Python venv..."
    "$PYTHON_CMD" -m venv "$INSTALL_DIR/.venv"
fi

echo "  Installiere Dependencies..."
"$VENV_PYTHON" -m pip install --upgrade pip --quiet 2>/dev/null
"$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR" --quiet 2>/dev/null
echo "  [OK] Dependencies installiert"
echo

# --- Wrapper erstellen ---
mkdir -p "$BIN_DIR"

cat > "$WRAPPER" << SCRIPT
#!/usr/bin/env bash
# Jira Timesheet - Wrapper (automatisch generiert)
"$INSTALL_DIR/.venv/bin/python" -m jira_timesheet "\$@"
SCRIPT
chmod +x "$WRAPPER"

echo "  [OK] Wrapper erstellt: $WRAPPER"

# --- PATH pruefen ---
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
    echo
    echo "  [HINWEIS] $BIN_DIR ist nicht im PATH."
    SHELL_NAME=$(basename "$SHELL" 2>/dev/null || echo "bash")
    case "$SHELL_NAME" in
        zsh)  RC_FILE="~/.zshrc" ;;
        fish) RC_FILE="~/.config/fish/config.fish" ;;
        *)    RC_FILE="~/.bashrc" ;;
    esac
    echo "  Fuege diese Zeile zu $RC_FILE hinzu:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# --- Fertig ---
echo
echo "  +================================================+"
echo "  |   Installation abgeschlossen! ($VERSION)"
echo "  +================================================+"
echo
echo "  Starten mit:"
echo "    jira-timesheet"
echo
echo "  Beim ersten Start [S] druecken fuer Settings."
echo
echo "  Aktualisieren:"
echo "    Installer erneut ausfuehren."
echo
echo "  Deinstallieren:"
echo "    rm -rf ~/.jira-timesheet-app"
echo "    rm ~/.local/bin/jira-timesheet"
echo
