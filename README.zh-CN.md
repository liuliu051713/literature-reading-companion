# 文献伴读工具

这是一个本地优先、可切换 AI 模型的开源工具。它的目标不是把论文机械翻译成中文，而是生成一份新的“阅读版文档”：

- 左侧保留原始段落；
- 左侧保留原始段落；选择全文翻译时，每段原文下方紧接忠实的中文翻译，HTML 可切换“只看原文 / 原文与翻译 / 只看翻译”；
- 左侧会高亮原文中的 1–3 个重点句、术语或公式，点击后定位到右侧对应的逐点讲解；右侧先解释正文的实质内容，再补充其在全文中的位置、上下文和证据边界；
- 批注面向不熟悉领域的读者，解释术语、推理步骤和公式的含义，而不只是说明“这一页的作用”；
- 公式可用 `\(...\)` 或 `\[...\]` 标记，HTML 会显示 MathML，DOCX 会写入可编辑的 Office Math；公式重点还要求说明符号、变化方向和一个小型数值例子；
- 用户可选择不翻译，或保留原文并增加完整中文翻译。

## 第一版支持什么

- 输入：可提取文字的 PDF、DOCX、TXT；
- 输出：HTML 阅读版与 DOCX 阅读版；
- 模型：OpenAI、Gemini，或不联网的 mock 演示模式；
- 隐私：不提供项目自建的文件存储服务；只有用户主动选择模型时，提取出的文本才会发送给该模型。

第一版只保证段落级锚点。扫描型 PDF、复杂双栏版式的完整重建、图表独立锚点、任意 PDF 公式的自动重建、批量处理和协作阅读会在后续版本实现。

下载后的 HTML 不能自行调用 ChatGPT 模型；若读者拖选左侧任意未标记句子，页面会准备一条追问文本。将它粘贴回当前 ChatGPT 对话后，App 会取得该句的上下文并继续解释。

## 也可以在 ChatGPT 网页版中运行

仓库现在包含一个 **ChatGPT App / MCP 开发者模式测试版**。它不是把 PDF 再发给 OpenAI API，而是由你正在使用的 ChatGPT 对话完成阅读理解；本机 MCP 服务只负责临时接收文件、保存与原文段落一一对应的批注，并输出 HTML/DOCX。

因此，这条路线不需要设置 `OPENAI_API_KEY`，也不会消耗本仓库 OpenAI provider 的 API 额度。它仍需要你本机临时运行服务，并通过 HTTPS 隧道让 ChatGPT 连接。

完整、按 Windows PowerShell 写的操作说明见：[docs/chatgpt-app.md](docs/chatgpt-app.md)。其中包含：

- 如何安装 MCP 组件；
- 如何开启 ChatGPT Developer mode；
- 如何将 PDF 拖进 ChatGPT 后生成中文深度批注；
- 临时文件、隐私和公开发布前必须补上的安全措施。

## 快速体验

    git clone https://github.com/liuliu051713/literature-reading-companion.git
    cd literature-reading-companion
    python -m venv .venv
    pip install -e .
    paper-reader annotate examples/sample-paper.txt --provider mock --format all --output-dir output

mock 模式不会调用任何 AI，也不会对文本作真实语义判断；它只用于确认“解析—锚点—排版”流程正常。配置 OpenAI 或 Gemini 后，工具才会生成实质性的阅读批注。

详细安装方法见 [docs/installation.md](docs/installation.md)，批注要求见 [docs/annotation-standard.md](docs/annotation-standard.md)。
