#!/bin/bash
# Simple HTTP server for local testing

cd public
echo "Starting local server..."
echo "Site will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""
python3 -m http.server 8000
