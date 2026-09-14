#!/bin/bash
# Mong Vo Lam - Private Server Startup Script
# For Pterodactyl deployment

echo "=========================================="
echo "  Mong Vo Lam - Private Server"
echo "=========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found!"
    exit 1
fi

# Create data directory
mkdir -p data

# Copy server if not exists
if [ ! -f "data/mvl_server_full.py" ]; then
    cp mvl_server_full.py data/
fi

# Start server
cd data
echo "Starting server..."
python3 mvl_server_full.py
