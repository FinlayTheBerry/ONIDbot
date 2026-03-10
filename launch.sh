#!/bin/sh
set -x

if [ ! -d "./venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install discord requests cryptography
    python3 ./onid_bot.py
else
    source venv/bin/activate
    python3 ./onid_bot.py
fi