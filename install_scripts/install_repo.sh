#!/bin/bash
set -e

python -m ensurepip || true
python -m pip install --upgrade pip

python -m pip install -r requirements.txt || true
python -m pip install .