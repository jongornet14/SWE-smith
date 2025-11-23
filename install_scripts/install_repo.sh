#!/bin/bash
set -e

python -m ensurepip --user || true
python -m pip install --user --upgrade pip

python -m pip install --user -r requirements.txt || true
python -m pip install --user .