#!/bin/bash
set -ux
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python setup.py develop

