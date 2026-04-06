#!/bin/sh

cd "$(dirname "$0")"

if [ ! -d "./venv" ]; then
    python -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    python ./onid_bot.py
else
    source venv/bin/activate
    python ./onid_bot.py
fi