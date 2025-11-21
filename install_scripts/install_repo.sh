#!/bin/bash
set -e

python3 -m ensurepip --user || true
python3 -m pip install --user --upgrade pip

python3 -m pip install --user -r requirements.txt || true
python3 -m pip install --user .