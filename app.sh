#!/usr/bin/env sh
set -eu
pip install -r requirements.txt
pip install -r requirements-dev.txt
python run.py
