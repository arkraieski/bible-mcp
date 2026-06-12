#!/usr/bin/env python3
"""
One-step setup: creates a virtualenv, installs dependencies,
and builds the database from the bundled Bible source files.

Usage: python setup.py
"""

import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
DATA = ROOT / "data"


def run(*args):
    subprocess.run(args, check=True)


def step(msg):
    print(f"\n>>> {msg}")


step("Creating virtual environment...")
venv.create(VENV, with_pip=True)
run(PYTHON, "-m", "pip", "install", "--quiet", "-r", ROOT / "requirements.txt")

ingest = [str(PYTHON), str(ROOT / "scripts/ingest.py")]

step("Ingesting World English Bible (this will take a few minutes)...")
run(*ingest, "--file", DATA / "web.xml", "--translation", "web",
    "--name", "World English Bible", "--license", "Public Domain")

step("Ingesting King James Version (this will take a few minutes)...")
run(*ingest, "--file", DATA / "kjv.xml", "--translation", "kjv",
    "--name", "King James Version", "--license", "Public Domain")

db_path = ROOT / "bible.db"
print(f"""
Setup complete. Add this to your Claude Desktop config:

  "command": "{PYTHON}",
  "args":    ["{ROOT / 'server.py'}"],
  "env":     {{"BIBLE_DB_PATH": "{db_path}"}}
""")
