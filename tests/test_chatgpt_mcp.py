from __future__ import annotations

import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path


@unittest.skipIf(importlib.util.find_spec("mcp") is None, "ChatGPT App dependencies are optional")
class ChatGPTMCPTests(unittest.TestCase):
    def test_configured_public_tunnel_host_is_accepted_but_other_hosts_are_rejected(self) -> None:
        from starlette.testclient import TestClient

        from literature_reader.chatgpt_app_service import ReadingJobStore
        from literature_reader.chatgpt_mcp import build_asgi_app, build_mcp_server

        initialize = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            store = ReadingJobStore(Path(directory), batch_size=4)
            server = build_mcp_server(
                store,
                public_base_url="https://example.trycloudflare.com",
                max_upload_bytes=1024 * 1024,
                host="127.0.0.1",
                port=8000,
            )
            app = build_asgi_app(store, server)
            with TestClient(app) as client:
                accepted = client.post(
                    "/mcp",
                    json=initialize,
                    headers={
                        "host": "example.trycloudflare.com",
                        "accept": "application/json",
                    },
                )
                rejected = client.post(
                    "/mcp",
                    json=initialize,
                    headers={
                        "host": "other.trycloudflare.com",
                        "accept": "application/json",
                    },
                )

        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(rejected.status_code, 421)

    def test_tools_expose_chatgpt_file_parameter_and_download_links(self) -> None:
        from literature_reader.chatgpt_app_service import ReadingJobStore
        from literature_reader.chatgpt_mcp import build_mcp_server

        async def verify() -> None:
            with tempfile.TemporaryDirectory() as directory:
                store = ReadingJobStore(Path(directory), batch_size=4)
                started = store.create_from_bytes(
                    filename="paper.txt",
                    content=b"Title\n\nA short paragraph for MCP verification.",
                    translation="none",
                )
                job_id = started["job_id"]
                store.save_paper_map(
                    job_id,
                    research_question="研究什么？",
                    central_claim="验证下载链接。",
                    argument_map=["问题", "结论"],
                    scope_notes="测试。",
                )
                store.save_annotations(
                    job_id,
                    [
                        {
                            "anchor": "P001",
                            "role": "作用",
                            "context": "上下文",
                            "explanation": "解释",
                            "takeaway": "要点",
                            "caveat": "提醒",
                        }
                    ],
                )
                server = build_mcp_server(
                    store,
                    public_base_url="https://example.test",
                    max_upload_bytes=1024 * 1024,
                    host="127.0.0.1",
                    port=8000,
                )

                tools = await server.list_tools()
                start_tool = next(tool for tool in tools if tool.name == "start_reading_copy")
                self.assertEqual(start_tool.meta, {"openai/fileParams": ["paper"]})
                self.assertIn("paper", start_tool.inputSchema["properties"])
                render_tool = next(tool for tool in tools if tool.name == "render_reading_copy")
                self.assertNotIn("ctx", render_tool.inputSchema["properties"])

                result = await server.call_tool(
                    "render_reading_copy",
                    {"job_id": job_id, "output_format": "all"},
                )
                links = [item for item in result.content if item.type == "resource_link"]
                self.assertEqual(len(links), 2)
                self.assertTrue(
                    all(str(link.uri).startswith("https://example.test/downloads/") for link in links)
                )

        asyncio.run(verify())


if __name__ == "__main__":
    unittest.main()
