#!/bin/bash
# Start a simple HTTP server on port 8000 and open the site in the default browser
cd "$(dirname "$0")"
python3 -m http.server 8000 &
# Give the server a moment to start
sleep 1
open http://localhost:8000
wait
