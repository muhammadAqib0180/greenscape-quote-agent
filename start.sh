#!/bin/sh
set -e

# Sanitize and validate PORT variable to ensure it is a valid integer
# If PORT is un-set, empty, or literally "$PORT", fallback to 8000
if [ -z "$PORT" ] || [ "$PORT" = '$PORT' ] || [ "$PORT" = '"$PORT"' ]; then
    PORT_NUM=8000
else
    # Strip any potential quotes or whitespace
    PORT_NUM=$(echo "$PORT" | tr -cd '0-9')
    if [ -z "$PORT_NUM" ]; then
        PORT_NUM=8000
    fi
fi

echo "Starting Uvicorn server on host 0.0.0.0 port $PORT_NUM..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT_NUM"
