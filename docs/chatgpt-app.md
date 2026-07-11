# 在 ChatGPT 网页版中测试文献伴读

这一条路线让 ChatGPT 对话里的模型完成阅读理解，因此**不需要**为本项目设置 `OPENAI_API_KEY`，也不会调用本仓库原有的 OpenAI API provider。

它仍然需要你的电脑临时运行一个小型 MCP 服务。原因很简单：ChatGPT 能读 PDF、写批注，但不能直接在 GitHub 仓库里执行 Python 或生成你电脑上的 DOCX。

```text
你拖入 PDF → ChatGPT 读论文并写中文批注 → 本机 MCP 服务校验段落对应关系
                                              ↓
                              生成 HTML / DOCX → ChatGPT 返回下载链接
```

这是一个**私人开发者模式测试版**，不是已经可以公开给所有人安装的正式 App。它没有用户登录、多人隔离或生产级存储；请不要把它直接部署为公开服务。

## 你需要准备什么

- Python 3.10 或更高版本；
- 一个可以开启“开发者模式”的 ChatGPT 账号；
- 最新版本的本仓库；
- 一个临时 HTTPS 隧道。本指南使用 Cloudflare Quick Tunnel，仅用于你自己的测试；
- 一篇你有权上传和处理的、可复制文字的 PDF。

你**不需要**：

- OpenAI API Key；
- OpenAI API 充值额度；
- Gemini API Key。

ChatGPT 账号本身的套餐、文件上传限制和对话使用限制仍然照常适用。

## 第 1 步：更新并安装 ChatGPT App 所需组件

如果你之前是下载 ZIP 文件，请到 GitHub 重新下载最新 ZIP 并解压；旧文件夹不会自动更新。打开 PowerShell，并进入项目目录后运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[chatgpt-app]"
```

这一步只会安装 MCP 服务所需的 Python 包。不要输入或设置 `OPENAI_API_KEY`。

## 第 2 步：安装一个临时 HTTPS 隧道

ChatGPT 网页不能访问你电脑上的 `localhost`，所以要用隧道临时把它连到 ChatGPT。测试时可使用 Cloudflare 的 Quick Tunnel；它会输出一个随机的 `https://...trycloudflare.com` 地址。

1. 从 [Cloudflare 的 cloudflared 下载说明](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/) 下载 Windows 版本的 `cloudflared.exe`。
2. 将 `cloudflared.exe` 放到项目根目录中，也就是和 `pyproject.toml` 同一个文件夹。

Quick Tunnel 只用于测试。它会把这次测试的服务暴露在一个随机公网地址上，因此不要用机密、未发表或受限制的论文测试。

## 第 3 步：启动本机 MCP 服务

在第一个 PowerShell 窗口中，仍处于项目根目录，运行：

```powershell
.\.venv\Scripts\python.exe -m literature_reader.chatgpt_mcp
```

看到类似下面的文字表示正常：

```text
Uvicorn running on http://127.0.0.1:8000
```

这个窗口必须一直开着。不要关闭它。

## 第 4 步：启动 HTTPS 隧道

再打开**第二个** PowerShell 窗口，进入同一个项目文件夹，运行：

```powershell
.\cloudflared.exe tunnel --url http://127.0.0.1:8000
```

等待它显示一个类似下面的地址：

```text
https://orange-example.trycloudflare.com
```

复制这个地址，并在浏览器中打开：

```text
https://orange-example.trycloudflare.com/health
```

如果看到包含 `"status":"ok"` 的小段文字，说明“ChatGPT → 隧道 → 你的电脑”这条路已经通了。

## 第 5 步：让本机服务信任这一次的隧道地址

Cloudflare 会保留随机公网地址作为请求的 Host。为了让服务只接受这一次的准确地址，需要回到**第一个** PowerShell 窗口，按 `Ctrl+C` 停止 Python 服务；第二个运行 `cloudflared` 的窗口保持不动。

将下面命令中的地址换成你刚才实际看到的地址，再运行：

```powershell
$env:LRC_PUBLIC_BASE_URL = "https://orange-example.trycloudflare.com"
.\.venv\Scripts\python.exe -m literature_reader.chatgpt_mcp
```

重新看到 `Uvicorn running on http://127.0.0.1:8000` 后，再继续下一步。每次重开 Quick Tunnel，地址都会变化，因此也需要重复本小节。

## 第 6 步：在 ChatGPT 中添加你的开发者 App

1. 打开 ChatGPT 网页版。
2. 进入 **Settings（设置）→ Security and login（安全与登录）**，开启 **Developer mode（开发者模式）**。
3. 进入 **Settings → Plugins**，或打开 <https://chatgpt.com/plugins>。
4. 点击加号，创建一个 developer-mode app。
5. 填写：

   - Name：`Literature Reading Companion`
   - Description：`上传论文后生成原文与中文深度批注一一对应的阅读版，并可选择完整翻译。`
   - MCP server URL：把第 4 步的地址加上 `/mcp`，例如 `https://orange-example.trycloudflare.com/mcp`
   - 身份验证：选择 **未授权 / None**，不要选择 OAuth。

6. 点击 Create。成功后，ChatGPT 应显示 7 个工具，包括 `start_reading_copy` 和 `render_reading_copy`。

如果没有显示工具，不要继续上传 PDF；先确认两个 PowerShell 窗口都没有报错，并再次打开 `/health` 测试链接。

## 第 7 步：真正测试一篇论文

1. 新建一个 ChatGPT 对话。
2. 点击输入框旁的 `+`，选择 **More**，选择刚创建的 `Literature Reading Companion`。
3. 将测试 PDF 拖进对话。
4. 输入下面这段话：

```text
请使用 Literature Reading Companion 为这个 PDF 生成带批注的阅读版。
保留英文原文，不要全文翻译；右侧批注全部使用中文。
每个正文段落都必须有对应批注，批注要解释它在全文论证中的作用、与前后文的关系、阅读要点和证据边界，不能只复述原文。
完成后请给我 HTML 和 DOCX 下载文件。
```

若要同时生成全文中文翻译，将第二行换成：

```text
保留英文原文，并为每个正文段落增加完整、忠实的中文翻译；右侧批注全部使用中文。
```

ChatGPT 会连续调用多个工具，所以处理一篇长论文需要一些时间。完成前不要关闭两个 PowerShell 窗口。最后它会给出 HTML 和 DOCX 的临时下载项。

## 文件与隐私规则

- 上传的文件、批注和输出文件只暂存于项目目录下的 `.lrc-chatgpt-jobs`，默认 60 分钟过期；正常关闭服务时也会清除本次任务。
- 下载完成后，再按 `Ctrl+C` 关闭两个 PowerShell 窗口。
- 关闭服务前请先下载结果；关闭后临时下载链接会失效。
- 若电脑意外断电或强制结束进程，残留的临时目录会在下次启动后超过 60 分钟时清理。对特别敏感的测试文档，请自行检查并删除 `.lrc-chatgpt-jobs`。
- Quick Tunnel 的设计目标是开发测试，不是公开发布。正式开放给多人使用前，需要加入登录鉴权、每位用户的隔离存储、限流、审核与稳定部署。

## 常见问题

### 我仍然看到 API 额度不足错误

这说明你运行的是旧命令：

```powershell
python -m literature_reader annotate ... --provider openai
```

它会调用 OpenAI API。ChatGPT 网页版 MCP 路线应该运行的是：

```powershell
.\.venv\Scripts\python.exe -m literature_reader.chatgpt_mcp
```

### ChatGPT 提示无法连接 MCP server

按顺序检查：

1. 第一个窗口中的 Python 服务仍在运行；
2. 第二个窗口中的 `cloudflared` 仍在运行；
3. 浏览器能打开 `https://你的随机地址/health`；
4. ChatGPT 中填写的是 `https://你的随机地址/mcp`，不是裸地址；
5. 身份验证选的是 **未授权 / None**，不是 OAuth；
6. 启动 Python 服务前，已经将 `LRC_PUBLIC_BASE_URL` 设置为当前随机地址；
7. 隧道每次重新启动会产生新地址，需要在 ChatGPT App 设置中更新 URL，并在第一个窗口重新设置 `LRC_PUBLIC_BASE_URL` 后重启服务。

### 最终文件下载失败

先不要关闭服务和隧道。重新执行本次对话，或在启动服务前设置固定的公开 HTTPS 地址：

```powershell
$env:LRC_PUBLIC_BASE_URL = "https://你的公开域名"
.\.venv\Scripts\python.exe -m literature_reader.chatgpt_mcp
```

只有在该地址确实由你控制且支持 HTTPS 时才设置它。

## 之后如何公开给所有人

个人测试成功后，下一阶段不是把电脑的隧道链接发给所有人，而是：

1. 部署 MCP 服务到有 HTTPS 的云端；
2. 加入用户登录、文件隔离、删除策略与速率限制；
3. 在 ChatGPT 的插件提交流程中提交 App；
4. 做真实论文的质量评估，尤其检查段落锚点、引用、图表和错误解释。

OpenAI 的 Apps SDK 文档说明了开发者模式连接和公开提交流程：<https://developers.openai.com/apps-sdk/deploy/connect-chatgpt/>。
