#!/usr/bin/env python3
"""Generate a standalone DSH MCP overlay; never edit an existing profile."""
import argparse
import json
from pathlib import Path
import sys
from shinku_tts import ROOT, ShinkuTTS


def build_patch(config: Path, python: Path) -> list:
    return [{"insert": [{"id": "mcp-shinku", "name": "@deepseek-ai/dsh-mcp-client",
                         "config": {"serverName": "shinku", "transport": "stdio",
                                    "command": str(python),
                                    "args": [str(ROOT / "scripts/shinku_mcp.py"), "--config", str(config)],
                                    "cwd": str(ROOT), "toolCallTimeoutMs": 180000,
                                    "env": {"PYTHONIOENCODING": "utf-8"}}}]}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(ROOT / "configs/tts.local.json"))
    parser.add_argument("--output", default=str(ROOT / "integrations/dsh/shinku.local.yml"))
    args = parser.parse_args()
    client = ShinkuTTS(args.config)
    client.payload("Configuration check", lang="en")
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # JSON is valid YAML; avoid platform path escaping and extra YAML dependencies.
    with output.open("x", encoding="utf-8") as handle:
        json.dump(build_patch(client.config_path, Path(sys.executable).resolve()), handle,
                  ensure_ascii=True, indent=2)
        handle.write("\n")
    print(f"Created DSH overlay: {output}")
    print(f"QQ plugin: add this directory to sendFile.extraRoots: {client.output_dir}")


if __name__ == "__main__":
    main()
