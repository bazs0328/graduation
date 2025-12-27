# Vue3 + FastAPI MVP（上传 → 摘要 → 问答）

这是一个可直接演示的 MVP 骨架，支持：

- 文本文件上传（text/*）
- 自动生成摘要
- 基于文本内容的问答，并返回引用来源

即使没有 `OPENAI_API_KEY` 也可完整演示闭环流程。

## 目录结构

```
.
├── backend
│   ├── main.py
│   └── requirements.txt
├── frontend
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src
│       ├── App.vue
│       └── main.js
└── .env.example
```

## 快速开始

### 1. 启动后端（FastAPI）

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

后端接口地址：`http://localhost:8000`

### 2. 启动前端（Vue3 + Vite）

```bash
cd frontend
npm install
npm run dev
```

前端页面地址：`http://localhost:5173`

## 接口说明

### 上传

`POST /api/upload`

- Content-Type: multipart/form-data
- form 字段：`file`

返回示例：

```json
{
  "doc_id": "uuid",
  "filename": "demo.txt",
  "summary": "...",
  "word_count": 123
}
```

### 问答

`POST /api/ask`

请求示例：

```json
{
  "doc_id": "uuid",
  "question": "文档主要讲什么？"
}
```

返回示例：

```json
{
  "answer": "...",
  "sources": [
    {
      "index": 1,
      "snippet": "..."
    }
  ]
}
```

## 说明

- 当前实现使用规则匹配实现摘要与问答，确保无外部 API 依赖。
- 上传内容暂存于内存中，重启后会清空。
- 如需修改前后端地址，请参考 `.env.example`。
