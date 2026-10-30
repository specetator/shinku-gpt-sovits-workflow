#!/usr/bin/env python3
"""DSH-compatible stdio MCP tools. Audio stays on the DSH/QQ plugin host."""
import argparse
from typing import Any
from mcp.server.fastmcp import FastMCP
from shinku_tts import ShinkuTTS


def create_server(client: ShinkuTTS) -> FastMCP:
    server = FastMCP("shinku", instructions=(
        "Generate Shinku speech when the user requests a voice reply. "
        "For a QQ conversation, call generate_qq_voice, then pass its qq_arguments to "
        "the existing qqbot_send_file tool. Omit target so the QQ plugin uses the current "
        "conversation. A generated file is not a sent message; report delivery only after "
        "qqbot_send_file succeeds. Do not send the same file twice via another attachment mechanism. "
        "For other clients use synthesize. Use list_emotions before selecting a non-neutral emotion."
    ))

    @server.tool()
    def list_emotions() -> dict[str, Any]:
        """List configured reference emotions; this does not run inference."""
        return {"emotions": client.available_emotions()}

    @server.tool()
    def synthesize(text: str, emotion: str = "neutral", lang: str = "auto") -> dict[str, Any]:
        """Create a WAV on this host and return its absolute file_path. Does not send messages."""
        return client.synthesize(text, emotion, lang)

    @server.tool()
    def generate_qq_voice(text: str, emotion: str = "neutral", lang: str = "auto") -> dict[str, Any]:
        """Generate WAV for QQ native voice. Next call qqbot_send_file with qq_arguments.

        Run this server on the same filesystem as dsh-qqbot. The QQ plugin owns
        conversation routing, media upload and voice delivery. This tool only synthesizes.
        """
        result = client.synthesize(text, emotion, lang)
        return {**result, "delivery": "pending", "qq_tool": "qqbot_send_file",
                "qq_arguments": {"file_path": result["file_path"]}}

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    args = parser.parse_args()
    create_server(ShinkuTTS(args.config)).run(transport="stdio")


if __name__ == "__main__":
    main()
