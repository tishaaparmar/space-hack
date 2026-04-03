#!/bin/bash
set -e

echo "[START] Booting Python Space-Hack Backend on Port 8000..."
cd /app/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "[START] Booting React Orbital Insight Dashboard on Port 3000..."
cd /app/frontend
npm start
