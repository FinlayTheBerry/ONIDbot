#!/bin/sh
set -x
cd "$(dirname "$0")"

mkdir -p ~/public_html/
chmod 755 ~/public_html
mkdir -p ~/public_html/onid_bot
chmod 755 ~/public_html/onid_bot
cp ./osu_font.otf ~/public_html/onid_bot/osu_font.otf
chmod 644 ~/public_html/onid_bot/osu_font.otf