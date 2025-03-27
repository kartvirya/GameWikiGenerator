#!/usr/bin/env bash
# Exit on error
set -e

# Install Python dependencies
pip install -r .render/requirements.txt

# Create data directory if it doesn't exist
mkdir -p data

# Ready for deployment message
echo "Build completed successfully!"