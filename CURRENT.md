\# CURRENT.md — 开题前可预览 MVP



目标：用最少功能跑通“上传 -> 摘要 -> 问答（带引用）”的演示闭环。



验收标准：

1\) 后端 FastAPI：

&nbsp;  - GET /health -> {"ok": true}

&nbsp;  - POST /upload -> 上传 pdf/txt，返回 doc\_id

&nbsp;  - GET /docs -> 列出 doc\_id/filename/created\_at

&nbsp;  - GET /summary?doc\_id=... -> 无 OPENAI\_API\_KEY 时返回 mock；有 key 可调用真实 LLM

&nbsp;  - POST /chat -> 入参 {doc\_id, question}，返回 {answer, sources}

&nbsp;    \* sources 至少2条：{snippet, location}（location 可先段号/页码占位）



2\) 前端 Vue：

&nbsp;  - 页面：上传\&列表 / 摘要 / 问答

&nbsp;  - 演示路径：上传 -> 点“生成摘要” -> 去问答提问 -> 展示 sources



3\) 工程化：

&nbsp;  - README：一键启动（本地命令即可）

&nbsp;  - .env.example：OPENAI\_API\_KEY（可选）

