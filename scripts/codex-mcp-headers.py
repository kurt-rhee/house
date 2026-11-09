#!/usr/bin/env python3
"""Codex HTTP-header helper: discover the running House app without storing its token in config."""
import json
from pathlib import Path
import sys
from uuid import UUID


def main():
    connection = Path.home() / "Library/Application Support/House/mcp.json"
    try:
        session = json.loads(connection.read_text())
        token = str(UUID(session["token"]))
        if session["url"] != "http://127.0.0.1:3847/mcp":
            raise ValueError("Unexpected House endpoint")
    except (OSError, ValueError, KeyError, TypeError):
        print("Start House with 'mise dev' before connecting Codex.", file=sys.stderr)
        return 1
    print(json.dumps({"Authorization": f"Bearer {token}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
