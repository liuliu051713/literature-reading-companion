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
                            "role": "这一段提供用于验证 MCP 下载流程的示例正文。",
                            "context": "它是测试文章的唯一段落，因此没有前后段；后续步骤会把这个锚点渲染成下载文件。",
                            "explanation": (
                                "这段文字本身不是在提出学术结论，而是为 MCP 工具测试提供一条可被稳定锚定的正文。"
                                "保存批注后，服务会检查 P001 是否仍然与这段原文对应，再生成 HTML 和 DOCX 的临时下载链接。"
                                "这说明阅读版的正确性首先依赖于原文与批注不脱节，而不是只生成一段看似合理的说明。"
                            ),
                            "takeaway": "即使是测试文本，也必须先通过锚点核对，才能安全生成阅读版。",
                            "caveat": "这只是工具流程的测试材料，不能外推为真实论文解释质量。",
                            "focus_points": [
                                {
                                    "quote": "A short paragraph for MCP verification.",
                                    "kind": "claim",
                                    "explanation": (
                                        "这条测试正文的意义不在学术内容，而在确认系统会把一条精确原文和一张右侧讲解卡稳定绑定。"
                                        "读者点击左侧这句时，应当能回到同一锚点，而不会误跳到另一篇或另一段材料。"
                                    ),
                                }
                            ],
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
                selected_tool = next(tool for tool in tools if tool.name == "get_selected_passage_context")
                self.assertIn("selected_quote", selected_tool.inputSchema["properties"])

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
