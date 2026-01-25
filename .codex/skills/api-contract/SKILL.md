---
name: api-contract
description: API 契约定义与更新（输入/输出 JSON、统一错误结构、状态码与 curl 示例）；用于新增或变更接口并要求可复现验证时。
---

# api-contract

## 目标
- 明确接口输入/输出 JSON 示例
- 统一错误结构（code/message/details）
- 明确状态码（409 用于前置条件不足）
- 提供 curl 示例并写入 README 或 scripts

## 触发条件
- 新增/变更 API 接口
- 需要输出接口契约、示例与验证方式

## 输入
- 接口名称与用途
- 参数/字段需求与限制
- 依赖的前置条件（索引/资料/权限等）

## 输出
- 输入/输出 JSON 示例
- 错误结构与状态码说明
- curl 示例（写入 README 或 scripts）
- 变更文件清单

## 步骤
1. 读取并理解：ai-docs/PROJECT.md、ai-docs/AGENTS.md、ai-docs/CONTEXT.md、ai-docs/CURRENT.md、ai-docs/TASKS.md；若任一文件缺失或无法读取，停止并询问
2. 明确接口输入/输出 JSON（含必填/可选字段与示例）
3. 统一错误结构为 `{code, message, details}`，并标明 409 的前置条件不足场景
4. 给出至少 1 条 curl 示例，并写入 README 或 scripts
5. 若涉及实现变更，确保最小改动并补充验证

## 护栏
- 一次只处理一个接口或同一变更集
- 改动最小化，不引入新框架
- 必须提供可复现验证（curl/scripts/pytest）
- 前置条件不足必须返回 409

## 验收命令
- `curl -X POST http://localhost:8000/<path> -H "Content-Type: application/json" -d '<json>'`
- `bash scripts/dev_smoke.sh`（若更新了 smoke）
- `pytest -q`（若有接口测试）

## 失败处理
- 若契约不清晰或输入字段不完整，先询问用户补充
- 发现错误码不一致时，给出最小修复建议
- 不得跳过 README/scripts 的可复现入口
