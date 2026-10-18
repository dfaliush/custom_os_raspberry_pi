#!/usr/bin/env bash
#
# install.sh: install cam into ~/camera and link /usr/local/bin/cam.
# Run on Raspberry Pi OS as the camera user (not root); asks sudo for the link.
# An existing ~/camera/cam.conf is kept; a changed default goes to cam.conf.new.
#
# /usr/local/bin rather than ~/.local/bin: `ssh pi cam photo` runs without a
# login shell, so ~/.profile never adds ~/.local/bin to PATH.

set -euo pipefail

[ "$(id -u)" -ne 0 ] || { echo "запускай без sudo: ~/camera має належати користувачу" >&2; exit 1; }
command -v rpicam-vid > /dev/null || { echo "немає rpicam-vid: sudo apt install rpicam-apps" >&2; exit 1; }

SRC="$(dirname "$(readlink -f "$0")")"
DST="$HOME/camera"
[ "$SRC" != "$DST" ] || { echo "запускай install.sh з копії поза $DST (наприклад /tmp/camera)" >&2; exit 1; }

mkdir -p "$DST"
install -m 755 "$SRC/cam" "$DST/cam"
install -m 644 "$SRC/cam_stream.py" "$DST/cam_stream.py"
if [ -f "$DST/cam.conf" ]; then
	if ! cmp -s "$SRC/cam.conf" "$DST/cam.conf"; then
		install -m 644 "$SRC/cam.conf" "$DST/cam.conf.new"
		echo "лишаю наявний $DST/cam.conf (новий шаблон: cam.conf.new)"
	fi
else
	install -m 644 "$SRC/cam.conf" "$DST/cam.conf"
fi
sudo ln -sfn "$DST/cam" /usr/local/bin/cam
echo "готово: cam stream | photo | video [сек] | stop | status"
