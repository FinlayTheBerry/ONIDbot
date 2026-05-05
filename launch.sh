#!/bin/sh

cd "$(dirname "$0")"

if [ ! -d "./venv" ]; then
    python -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

source venv/bin/activate
exec python ./ONIDbot.py
