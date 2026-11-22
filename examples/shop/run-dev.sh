#!/usr/bin/env bash
# Starts the shop on $PORT (the evidence recorder sets it).
cd "$(dirname "$0")" && exec python3 app.py
