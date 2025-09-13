#!/bin/bash
# venvoy entrypoint that uses mounted source code if available

if [[ -n "$VENVOY_SOURCE_DIR" ]] && [[ -d "$VENVOY_SOURCE_DIR/src/venvoy" ]]; then
    # Use mounted source code
    echo "🔧 Using mounted venvoy source code"
    cd "$VENVOY_SOURCE_DIR"
    python3 -c "import sys; sys.path.insert(0, 'src'); from venvoy.cli import main; main()" "$@"
else
    # Use installed package
    venvoy "$@"
fi
