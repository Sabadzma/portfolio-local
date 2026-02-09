#!/bin/bash
cd "$(dirname "$0")/public"
echo "Site running at http://localhost:8000"
python3 -m http.server 8000
