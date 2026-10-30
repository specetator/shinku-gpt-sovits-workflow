#!/usr/bin/env python3
"""Exercise real MCP discovery + TTS; creates audio, never sends a QQ message."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check(args):
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(Path(__file__).with_name("shinku_mcp.py")),
                                         "--config", str(Path(args.config).resolve())])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=180)) as session:
            await session.initialize()
            listing = await session.list_tools()
            print(json.dumps({"tools": [tool.name for tool in listing.tools]}))
            result = await session.call_tool("generate_qq_voice", {
                "text": args.text, "lang": args.lang, "emotion": args.emotion,
            })
            if result.isError:
                raise RuntimeError(str(result.content))
            data = result.structuredContent
            if not data or not Path(data["file_path"]).is_file():
                raise RuntimeError("MCP did not return an existing audio file")
            print(json.dumps(data, ensure_ascii=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--text", default="今日はいい天気ですね。")
    parser.add_argument("--lang", default="ja")
    parser.add_argument("--emotion", default="neutral")
    asyncio.run(check(parser.parse_args()))


if __name__ == "__main__":
    main()
