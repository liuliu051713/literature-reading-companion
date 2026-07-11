"""ChatGPT App / MCP server for the literature reading companion.

The server contains no OpenAI API client and does not need an API key.  It uses
ChatGPT's model in the active chat to write the paper map and the annotations,
while this server receives the uploaded file, validates anchors, and renders a
downloadable reading copy.

Run after installing the optional dependency group::

    python -m literature_reader.chatgpt_mcp
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlparse

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, ResourceLink, TextContent, ToolAnnotations
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route

from .chatgpt_app_service import ReadingJobError, ReadingJobStore


APP_INSTRUCTIONS = """你是“Literature Reading Companion”的阅读协作助手。

当用户上传论文并要求生成带批注的阅读版时，请严格执行以下流程：
1. 调用 start_reading_copy，传入用户上传的 paper 文件和翻译选项。
2. 调用 get_document_outline，再基于已上传原文写出中文论文阅读地图，并调用 save_paper_map 保存它。
3. 对每一个 batch_index，调用 get_annotation_batch；根据该批原文和前后文，用中文写出每个锚点的 role、context、explanation、takeaway、caveat；随后立即调用 save_annotation_batch 保存。批注必须联系论文整体论证，不能只是复述原文。
4. 在所有锚点保存后，调用 get_reading_progress。只有 complete 为 true 时才调用 render_reading_copy。
5. 告诉用户已生成可下载的 HTML 与 DOCX 阅读版，并简要说明翻译选项。

不得跳过任何正文锚点。不要把章节标题误当作正文。不得编造原文没有说明的事实；不确定处应写入 caveat。除必要的原文术语外，所有面向读者的内容使用简体中文。
"""


class UploadedPaper(BaseModel):
    """File reference supplied and authorized by ChatGPT."""

    download_url: str = Field(description="ChatGPT provides a temporary authorized download URL.")
    file_id: str = Field(description="ChatGPT file identifier; retain only for the current tool call.")
    mime_type: str | None = Field(default=None, description="Optional MIME type supplied by ChatGPT.")
    file_name: str | None = Field(default=None, description="Original uploaded filename.")


class AnnotationInput(BaseModel):
    """One source-linked note written by ChatGPT for one paragraph anchor."""

    anchor: str = Field(description="Exact paragraph anchor returned by get_annotation_batch, such as P001.")
    role: str = Field(description="该段在论文论证中的作用，使用简体中文。")
    context: str = Field(description="该段与前后段及论文整体结构的关系，使用简体中文。")
    explanation: str = Field(description="帮助读者理解论证、方法或证据的解释，使用简体中文。")
    takeaway: str = Field(description="读者应带走的关键信息，使用简体中文。")
    caveat: str = Field(description="证据边界、不确定性或阅读提醒，使用简体中文。")
    translation: str | None = Field(
        default=None,
        description="仅当用户选择 full 时填写的忠实中文全文翻译。",
    )


def build_mcp_server(
    store: ReadingJobStore,
    *,
    public_base_url: str,
    max_upload_bytes: int,
    host: str,
    port: int,
) -> FastMCP:
    """Build the MCP server and its model-callable tools."""

    mcp = FastMCP(
        "Literature Reading Companion",
        instructions=APP_INSTRUCTIONS,
        host=host,
        port=port,
        json_response=True,
        transport_security=_transport_security_settings(public_base_url),
    )
    read_only = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=False,
        idempotentHint=True,
    )
    writes_local_state = ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=False,
        idempotentHint=True,
    )

    @mcp.tool(
        title="开始生成论文阅读版",
        description=(
            "接收用户在 ChatGPT 对话中上传的 PDF、DOCX 或 TXT，建立一个临时阅读任务。"
            "必须在用户明确要求生成带批注阅读版时调用。"
        ),
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
            idempotentHint=False,
        ),
        meta={"openai/fileParams": ["paper"]},
    )
    async def start_reading_copy(
        paper: UploadedPaper,
        translation: Literal["none", "full"] = "none",
    ) -> CallToolResult:
        """Create a short-lived reading job from a user-provided file."""

        content = await _download_chatgpt_file(paper, max_upload_bytes)
        result = store.create_from_bytes(
            filename=paper.file_name,
            content=content,
            translation=translation,
        )
        return _structured_result(
            result,
            "论文已解析。请先调用 get_document_outline，然后保存论文整体阅读地图。",
        )

    @mcp.tool(
        title="获取论文结构",
        description="返回论文的章节范围、段落锚点和简短预览，供生成整篇论文的中文阅读地图。",
        annotations=read_only,
    )
    def get_document_outline(job_id: str) -> CallToolResult:
        """Return the compact paper outline for one uploaded file."""

        result = store.document_outline(job_id)
        return _structured_result(result, "请据此及原始上传文件形成论文整体阅读地图，并调用 save_paper_map。")

    @mcp.tool(
        title="保存论文阅读地图",
        description="保存根据整篇原文形成的中文研究问题、核心主张、论证主线和适用范围。",
        annotations=writes_local_state,
    )
    def save_paper_map(
        job_id: str,
        research_question: str,
        central_claim: str,
        argument_map: list[str],
        scope_notes: str,
    ) -> CallToolResult:
        """Persist the map that ChatGPT derives from the uploaded paper."""

        result = store.save_paper_map(
            job_id,
            research_question=research_question,
            central_claim=central_claim,
            argument_map=argument_map,
            scope_notes=scope_notes,
        )
        return _structured_result(result, "阅读地图已保存。现在从 batch_index 0 开始逐批生成对应批注。")

    @mcp.tool(
        title="获取一批原文段落",
        description=(
            "返回少量原文段落、稳定锚点以及相邻上下文。必须逐批调用，并为返回的每个锚点"
            "生成联系全文论证的中文批注，随后调用 save_annotation_batch。"
        ),
        annotations=read_only,
    )
    def get_annotation_batch(job_id: str, batch_index: int) -> CallToolResult:
        """Retrieve one small, source-aligned batch for annotation."""

        result = store.annotation_batch(job_id, batch_index)
        return _structured_result(
            result,
            "请为本批每个锚点写中文深度批注，而不是逐句复述；然后立即调用 save_annotation_batch。",
        )

    @mcp.tool(
        title="保存一批对应批注",
        description=(
            "保存一批由 ChatGPT 依据原文写出的、与段落锚点一一对应的中文批注。"
            "每个返回锚点都必须恰好有一项。"
        ),
        annotations=writes_local_state,
    )
    def save_annotation_batch(job_id: str, annotations: list[AnnotationInput]) -> CallToolResult:
        """Validate and persist model-created notes for source anchors."""

        result = store.save_annotations(
            job_id,
            [annotation.model_dump() for annotation in annotations],
        )
        return _structured_result(result, "已保存本批批注。请继续处理未完成的段落，直到 complete 为 true。")

    @mcp.tool(
        title="查看阅读版完成进度",
        description="检查论文地图和全部段落批注是否已经齐全；只有 complete 为 true 才可生成文件。",
        annotations=read_only,
    )
    def get_reading_progress(job_id: str) -> CallToolResult:
        """Report the anchors that still need notes."""

        result = store.progress(job_id)
        return _structured_result(result, "若 complete 为 false，请继续获取并保存缺失段落的批注。")

    @mcp.tool(
        title="生成带批注文献",
        description=(
            "在论文地图和每个段落批注完整后，生成可下载的 HTML 和/或 DOCX 阅读版。"
            "不要在完成前调用。"
        ),
        annotations=writes_local_state,
    )
    def render_reading_copy(
        job_id: str,
        output_format: Literal["html", "docx", "all"] = "all",
        ctx: Context = None,
    ) -> CallToolResult:
        """Render the final two-column reading copy and return secure temporary links."""

        outputs = store.render(job_id, output_format)
        base_url = _public_base_url(public_base_url, ctx)
        content: list[TextContent | ResourceLink] = [
            TextContent(
                type="text",
                text="带批注的阅读版已生成。以下是临时下载文件；文件会随任务过期自动删除。",
            )
        ]
        result_files: list[dict[str, str]] = []
        for format_name, path in outputs.items():
            url = _download_url(base_url, job_id, path.name)
            mime_type = "text/html" if format_name == "html" else (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            content.append(
                ResourceLink(
                    type="resource_link",
                    uri=url,
                    name=path.name,
                    description="可下载的带批注文献阅读版",
                    mimeType=mime_type,
                )
            )
            result_files.append({"format": format_name, "file_name": path.name, "download_url": url})
        return CallToolResult(
            content=content,
            structuredContent={"job_id": job_id, "files": result_files},
        )

    return mcp


def build_asgi_app(store: ReadingJobStore, mcp: FastMCP) -> Starlette:
    """Expose both the /mcp endpoint and short-lived output downloads from one process."""

    async def health(_: object) -> JSONResponse:
        removed = store.cleanup_expired()
        return JSONResponse({"status": "ok", "expired_jobs_removed": removed})

    async def download(request) -> FileResponse:
        try:
            path = store.download_path(request.path_params["job_id"], request.path_params["filename"])
        except ReadingJobError as error:
            return JSONResponse({"error": str(error)}, status_code=404)
        return FileResponse(
            path,
            filename=path.name,
            media_type=_mime_for(path),
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette):
        async with mcp.session_manager.run():
            try:
                yield
            finally:
                store.clear_all()

    return Starlette(
        routes=[
            Route("/health", health),
            Route("/downloads/{job_id}/{filename}", download),
            Mount("/", app=mcp.streamable_http_app()),
        ],
        lifespan=lifespan,
    )


async def _download_chatgpt_file(paper: UploadedPaper, max_upload_bytes: int) -> bytes:
    """Download only the temporary HTTPS URL authorized by ChatGPT for this call."""

    parsed = urlparse(paper.download_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ReadingJobError("ChatGPT file download_url must be a temporary HTTPS URL.")
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        async with client.stream("GET", paper.download_url) as response:
            response.raise_for_status()
            header = response.headers.get("content-length")
            if header and header.isdigit():
                if int(header) > max_upload_bytes:
                    raise ReadingJobError(_size_error(max_upload_bytes))
            chunks = bytearray()
            async for chunk in response.aiter_bytes():
                chunks.extend(chunk)
                if len(chunks) > max_upload_bytes:
                    raise ReadingJobError(_size_error(max_upload_bytes))
    if not chunks:
        raise ReadingJobError("ChatGPT supplied an empty file.")
    return bytes(chunks)


def _structured_result(payload: dict, message: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=message)],
        structuredContent=payload,
    )


def _public_base_url(configured_url: str, ctx: Context | None) -> str:
    """Use an explicit deployment URL, or infer the HTTPS tunnel URL for local tests."""

    if configured_url:
        parsed = urlparse(configured_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ReadingJobError("LRC_PUBLIC_BASE_URL must be a public HTTPS URL.")
        return configured_url

    request = ctx.request_context.request if ctx and ctx.request_context else None
    headers = getattr(request, "headers", None)
    if headers is None:
        raise ReadingJobError(
            "Unable to infer a public URL. Set LRC_PUBLIC_BASE_URL to your public HTTPS tunnel or deployment URL."
        )
    host = headers.get("x-forwarded-host") or headers.get("host")
    scheme = (headers.get("x-forwarded-proto") or "https").split(",", maxsplit=1)[0].strip()
    if not host or scheme != "https":
        raise ReadingJobError(
            "Unable to infer a public HTTPS URL. Set LRC_PUBLIC_BASE_URL to your public HTTPS tunnel or deployment URL."
        )
    return f"https://{host}"


def _transport_security_settings(public_base_url: str) -> TransportSecuritySettings:
    """Allow local development plus one explicitly configured public HTTPS host.

    FastMCP enables DNS-rebinding protection automatically for a loopback host.
    A Quick Tunnel preserves its public Host header, so the exact tunnel host
    must be allow-listed instead of disabling that protection for every host.
    """

    allowed_hosts = [
        "127.0.0.1",
        "127.0.0.1:*",
        "localhost",
        "localhost:*",
        "[::1]",
        "[::1]:*",
    ]
    allowed_origins = [
        "http://127.0.0.1:*",
        "http://localhost:*",
        "http://[::1]:*",
        "https://chatgpt.com",
        "https://chat.openai.com",
    ]
    if public_base_url:
        parsed = urlparse(public_base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ReadingJobError("LRC_PUBLIC_BASE_URL must be a public HTTPS URL.")
        allowed_hosts.append(parsed.netloc)
        allowed_origins.append(f"https://{parsed.netloc}")
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


def _download_url(public_base_url: str, job_id: str, filename: str) -> str:
    return f"{public_base_url}/downloads/{quote(job_id, safe='')}/{quote(filename, safe='')}"


def _mime_for(path: Path) -> str:
    if path.suffix.lower() == ".html":
        return "text/html"
    if path.suffix.lower() == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


def _size_error(max_upload_bytes: int) -> str:
    return f"The uploaded file exceeds the configured {max_upload_bytes // (1024 * 1024)} MB limit."


def _positive_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise SystemExit(f"{name} must be an integer.") from error
    if parsed < 1:
        raise SystemExit(f"{name} must be at least 1.")
    return parsed


def main() -> None:
    """Run the private developer-mode HTTP server."""

    try:
        import uvicorn
    except ImportError as error:  # pragma: no cover - import error is user-facing
        raise SystemExit(
            "ChatGPT App dependencies are missing. Run: pip install -e \".[chatgpt-app]\""
        ) from error

    host = os.getenv("LRC_HOST", "127.0.0.1")
    port = _positive_int("LRC_PORT", 8000)
    ttl_minutes = _positive_int("LRC_TTL_MINUTES", 60)
    batch_size = _positive_int("LRC_BATCH_SIZE", 4)
    max_upload_mb = _positive_int("LRC_MAX_UPLOAD_MB", 25)
    public_base_url = os.getenv("LRC_PUBLIC_BASE_URL", "").strip().rstrip("/")
    root = Path(os.getenv("LRC_JOB_DIRECTORY", ".lrc-chatgpt-jobs"))

    store = ReadingJobStore(root, ttl_minutes=ttl_minutes, batch_size=batch_size)
    mcp = build_mcp_server(
        store,
        public_base_url=public_base_url,
        max_upload_bytes=max_upload_mb * 1024 * 1024,
        host=host,
        port=port,
    )
    app = build_asgi_app(store, mcp)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
