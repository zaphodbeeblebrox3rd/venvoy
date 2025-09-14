#!/bin/bash
# venvoy entrypoint that uses mounted source code if available

if [[ -n "$VENVOY_SOURCE_DIR" ]] && [[ -d "$VENVOY_SOURCE_DIR/src/venvoy" ]]; then
    # Use mounted source code
    echo "🔧 Using mounted venvoy source code"
    export PYTHONPATH="$VENVOY_SOURCE_DIR/src:$PYTHONPATH"
    cd "$VENVOY_SOURCE_DIR"
    python3 -m venvoy.cli "$@"
else
    # Use installed package
    venvoy "$@"
fi
