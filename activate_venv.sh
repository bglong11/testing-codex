#!/usr/bin/env bash

# Simple helper to activate the project virtual environment.
# Usage: source activate_venv.sh

VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found: $VENV_DIR"
  return 1 2>/dev/null || exit 1
fi

if [ -f "$VENV_DIR/bin/activate" ]; then
  # shellcheck disable=SC1090
  . "$VENV_DIR/bin/activate"
else
  echo "Activation script missing: $VENV_DIR/bin/activate"
fi
