#!/bin/sh

cd "$(dirname "$0")"

if [ ! -d "./env" ]; then
    python -m venv env
    source env/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

source env/bin/activate
exec python ./ONIDbot.py
