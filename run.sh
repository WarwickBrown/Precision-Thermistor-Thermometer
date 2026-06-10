#!/usr/bin/env bash
# =============================================================================
# run.sh  --  host-side helper for the Precision Thermistor Thermometer.
#
# One entry point for the off-Pico workflow. The Python dependencies live in a
# self-contained .venv (git-ignored), so nothing is installed into your system
# Python, and each common task is a single command.
#
#   ./run.sh setup            create .venv and install the host tools
#   ./run.sh flash [PORT]     copy firmware/ to the Pico and reboot it
#   ./run.sh log [ARGS...]    capture the USB CSV stream into data/ (e.g. --plot)
#   ./run.sh analyse FILE     run the stability / Allan-deviation analysis
#   ./run.sh pull-log [PORT]  copy the Pico's flash log.csv into data/
#   ./run.sh clear-log [PORT] delete the Pico's flash log.csv
#
# Typical session:
#   ./run.sh setup           # once
#   ./run.sh flash           # whenever the firmware changes
#   ./run.sh log             # capture a run (Ctrl-C to stop)
#   ./run.sh analyse data/log_YYYYmmdd_HHMMSS.csv
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
PY="$VENV/bin/python"
MPREMOTE="$VENV/bin/mpremote"

require_venv() {
    if [ ! -x "$PY" ]; then
        echo "No virtual environment yet. Run:  ./run.sh setup" >&2
        exit 1
    fi
}

usage() {
    cat <<'EOF'
run.sh  --  host helper for the Precision Thermistor Thermometer

  ./run.sh setup            create .venv and install the host tools
  ./run.sh flash [PORT]     copy firmware/ to the Pico and reboot it
  ./run.sh log [ARGS...]    capture the USB CSV stream into data/ (e.g. --plot)
  ./run.sh analyse FILE     run the stability / Allan-deviation analysis
  ./run.sh pull-log [PORT]  copy the Pico's flash log.csv into data/
  ./run.sh clear-log [PORT] delete the Pico's flash log.csv (asks first)

First time:  ./run.sh setup
Then:        ./run.sh flash    and    ./run.sh log
Stop a capture with Ctrl-C. Close Thonny or any serial monitor first, since
only one program can use the USB port at a time.
EOF
}

cmd_setup() {
    echo "Creating virtual environment in .venv ..."
    python3 -m venv "$VENV"
    "$PY" -m pip install --upgrade pip >/dev/null
    "$PY" -m pip install -r "$ROOT/tools/requirements.txt"
    echo
    echo "Done. Host tools are installed in .venv (git-ignored)."
    echo "Next:"
    echo "  ./run.sh flash     copy the firmware to the Pico"
    echo "  ./run.sh log       capture readings into data/"
}

cmd_flash() {
    require_venv
    local port="${1:-}"
    echo "Copying firmware to the Pico ..."
    if [ -n "$port" ]; then
        "$MPREMOTE" connect "$port" cp "$ROOT"/firmware/*.py :
        "$MPREMOTE" connect "$port" reset
    else
        "$MPREMOTE" cp "$ROOT"/firmware/*.py :
        "$MPREMOTE" reset
    fi
    echo "Done. The Pico boots main.py and starts streaming."
    echo "Now run:  ./run.sh log"
}

cmd_log() {
    require_venv
    exec "$PY" "$ROOT/tools/serial_logger.py" "$@"
}

cmd_analyse() {
    require_venv
    exec "$PY" "$ROOT/tools/analyse_log.py" "$@"
}

cmd_pull_log() {
    require_venv
    local port="${1:-}"
    local stamp dest
    stamp="$(date +%Y%m%d_%H%M%S)"
    dest="$ROOT/data/log_from_pico_$stamp.csv"
    echo "Copying log.csv off the Pico ..."
    if [ -n "$port" ]; then
        "$MPREMOTE" connect "$port" cp :log.csv "$dest"
    else
        "$MPREMOTE" cp :log.csv "$dest"
    fi
    echo "Saved $dest"
}

cmd_clear_log() {
    require_venv
    local yes="" port=""
    for a in "$@"; do
        case "$a" in
            -y|--yes) yes=1 ;;
            *)        port="$a" ;;
        esac
    done
    if [ -z "$yes" ]; then
        echo "This deletes log.csv on the Pico and cannot be undone."
        echo "Tip: ./run.sh pull-log  saves a copy into data/ first."
        read -r -p "Delete log.csv on the Pico? [y/N] " reply || reply=""
        case "$reply" in
            y|Y|yes|YES) ;;
            *) echo "Aborted."; return 0 ;;
        esac
    fi
    echo "Deleting log.csv on the Pico ..."
    local fail="Delete failed. Either there is no log.csv yet, or the port is busy (close Thonny or any serial monitor)."
    if [ -n "$port" ]; then
        "$MPREMOTE" connect "$port" rm :log.csv || { echo "$fail" >&2; exit 1; }
    else
        "$MPREMOTE" rm :log.csv || { echo "$fail" >&2; exit 1; }
    fi
    echo "Done. The firmware starts a fresh log.csv on its next run."
}

case "${1:-help}" in
    setup)               cmd_setup ;;
    flash)               shift; cmd_flash "${1:-}" ;;
    log|capture)         shift; cmd_log "$@" ;;
    analyse|analyze)     shift; cmd_analyse "$@" ;;
    pull-log|pulllog)    shift; cmd_pull_log "${1:-}" ;;
    clear-log|clearlog)  shift; cmd_clear_log "$@" ;;
    -h|--help|help)      usage ;;
    *) echo "Unknown command: $1" >&2; echo; usage; exit 1 ;;
esac
