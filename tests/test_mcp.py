import json
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from test_tts import Backend, ROOT, write_config


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_discovery_generation_and_visible_failure(self):
        (ROOT / "work").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as scratch, Backend() as backend:
            config = write_config(Path(scratch), backend.url)
            params = StdioServerParameters(command=sys.executable,
                                           args=[str(ROOT / "scripts/shinku_mcp.py"), "--config", str(config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listing = await session.list_tools()
                    self.assertEqual({tool.name for tool in listing.tools},
                                     {"synthesize", "generate_qq_voice", "list_emotions"})
                    result = await session.call_tool("generate_qq_voice", {"text": "こんにちは。"})
                    self.assertFalse(result.isError)
                    data = result.structuredContent
                    self.assertEqual(data["delivery"], "pending")
                    self.assertEqual(data["qq_tool"], "qqbot_send_file")
                    self.assertEqual(data["qq_arguments"], {"file_path": data["file_path"]})
                    self.assertTrue(Path(data["file_path"]).is_file())
                    # DSH can consume text; no unsupported inline MCP audio is required.
                    self.assertTrue(all(block.type == "text" for block in result.content))
                    self.assertEqual(json.loads(result.content[0].text)["file_path"], data["file_path"])
                    failed = await session.call_tool("generate_qq_voice", {"text": "hi", "emotion": "missing"})
                    self.assertTrue(failed.isError)
                    backend.status = 500
                    failed = await session.call_tool("synthesize", {"text": "hi"})
                    self.assertTrue(failed.isError)


if __name__ == "__main__":
    unittest.main()
