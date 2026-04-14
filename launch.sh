#!/bin/sh

cd "$(dirname "$0")"

if [ ! -d "./venv" ]; then
    python -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    python ./ONIDbot.py
else
    source venv/bin/activate
    python ./ONIDbot.py
fi