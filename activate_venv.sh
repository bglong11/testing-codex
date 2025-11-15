#!/usr/bin/env bash

# Simple helper to activate the project virtual environment.
# Usage: source activate_venv.sh

VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found: $VENV_DIR"
  return 1 2>/dev/null || exit 1
fi

if [ -n "$ZSH_VERSION" ] || [ -n "$BASH_VERSION" ]; then
  # Source the appropriate activation script for unix shells
  source "$VENV_DIR/bin/activate"
else
  echo "This script is intended for bash/zsh shell environments."
fi
