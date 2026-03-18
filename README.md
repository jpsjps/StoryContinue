# StoryContinue 本地小说续写系统

一个用于本地部署的小说续写工具，支持：

- 按章续写 / 一键续写到结局
- 选择结局/风格（圆满、悲剧、开放式等）
- 多项目/书籍管理与本地持久化
- 基于 OpenAI / Anthropic 协议的 LLM 流式续写

前端为本地单页 Web 页面，后端使用 Python + FastAPI，并通过 SSE 提供流式输出。

---

## 一、环境准备

### 1. 克隆与依赖安装

```bash
cd /home/ubuntu/my_pro/storyContinue
pip install -r requirements.txt
```

Python 需要 3.9+。

---

## 二、API 与模型配置（config.json）

后端调用大模型的参数（厂商、Base URL、API Key、模型名）通过 JSON 进行配置：

- 实际生效文件：`data/config.json`
- 模板示例：`config.example.json`

首次启动时，项目会自动将 `config.example.json` 复制为 `data/config.json`（如不存在）。

编辑 `data/config.json`：

```json
{
  "provider": "openai",
  "api_base": "https://api.openai.com/v1",
  "api_key": "YOUR_REAL_KEY_HERE",
  "model": "gpt-4.1"
}
```

- **provider**：目前支持 `"openai"` 和 `"anthropic"`（已预留结构，后续可扩展）。
- **api_base**：
  - OpenAI 官方：`https://api.openai.com/v1`
  - 若使用代理/自建中转，请填写对应地址。
- **api_key**：你的真实 API Key（请勿提交到仓库）。
- **model**：实际调用的模型名，例如 `gpt-4.1`、`gpt-4o`、`claude-3.7-sonnet` 等。

> 环境变量会覆盖 JSON 中对应字段，方便临时调试：
> - `LLM_PROVIDER`（覆盖 `provider`）
> - `OPENAI_BASE_URL`（覆盖 `api_base`）
> - `OPENAI_API_KEY` / `OPENAI_KEY` / `ANTHROPIC_API_KEY`（覆盖 `api_key`）
> - `OPENAI_MODEL`（覆盖 `model`）

---

## 三、一键启动脚本

项目提供脚本 `scripts/run.sh` 用于本地快速启动（后端 + 内置前端）：

```bash
cd /home/ubuntu/my_pro/storyContinue
./scripts/run.sh
```

脚本行为：

- 如存在 `requirements.txt`，自动执行依赖安装（若已安装会跳过）。
- 启动 FastAPI 后端，并把 `frontend/` 目录挂载为静态资源：
  - 页面与静态资源：`http://127.0.0.1:8000/`（根路径即首页）
  - 静态文件（CSS/JS/SVG）：`/static/...`
- `Ctrl + C` 时自动关闭服务进程。

> 如需修改端口，可通过环境变量指定：
>
> ```bash
> BACKEND_PORT=9000 ./scripts/run.sh
> ```

---

## 四、前端访问与基本使用

1. 启动脚本后，在浏览器访问前端：

   - `http://127.0.0.1:8080`

2. 在左侧：

   - 点击「新建项目」，输入标题和原文。
   - 选择项目后，可在右侧查看原文与已续写章节。

3. 在右侧续写设置区：

   - 选择结局/风格（圆满、悲剧、开放式）。
   - 选择模式：
     - `续写一章`：基于当前进度生成下一章。
     - `续写到结局`：直接生成结局章节。
   - 可填写补充说明（例如希望重点描写的人物、节奏等）。

4. 点击「开始续写」：

   - 前端通过 SSE 调用后端 `/api/stream/write` 接口。
   - 中间区域实时显示生成的文本。
   - 流结束后，后端会将本次生成内容保存为新的章节，并刷新项目列表和详情。

---

## 五、目录结构概览

```text
StoryContinue/
├── README.md
├── Architecture.md
├── config.example.json
├── requirements.txt
├── data/
│   ├── config.json          # 实际生效的 API/模型配置
│   └── projects/            # 各项目的 JSON 数据
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 加载 JSON + 环境变量的配置逻辑
│   ├── routes/
│   │   ├── projects.py      # 项目 CRUD 接口
│   │   └── write.py         # 续写与流式接口（SSE）
│   └── services/
│       ├── context.py       # 上下文截断与摘要策略
│       ├── prompt_builder.py# Prompt 模板与风格注入
│       ├── llm_adapter.py   # OpenAI/Anthropic 适配与流式调用
│       └── project_store.py # 项目/章节的本地 JSON 持久化
├── frontend/
│   ├── index.html           # 单页 Web UI
│   ├── app.js               # 调用后端 API 与流式展示
│   └── styles.css           # 基础样式
└── scripts/
    └── run.sh               # 一键启动前后端
```

如需更多架构细节与实现规划，可参见 `Architecture.md`。

