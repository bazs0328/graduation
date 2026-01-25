---
name: db-migrate
description: 最小化数据库 schema 调整与 Alembic 迁移流程（upgrade/downgrade/插入查询验证）。用于新增字段、轻量表结构变更或验证迁移可逆性时。
---

# db-migrate

## 目标
- 设计最小 schema（优先新增字段，不做大改）
- 迁移可升级可回滚
- 提供插入/查询验证方法

## 触发条件
- 需要新增字段/表或调整最小结构
- 要求提供 Alembic 迁移与验证步骤

## 输入
- 业务需求的最小字段清单
- 现有模型与数据库结构
- 迁移策略约束（仅新增字段/最小影响）

## 输出
- 迁移文件与变更摘要
- upgrade/downgrade 验证命令
- 插入/查询验证方法（SQL 或脚本）

## 步骤
1. 读取并理解：ai-docs/PROJECT.md、ai-docs/AGENTS.md、ai-docs/CONTEXT.md、ai-docs/CURRENT.md、ai-docs/TASKS.md；若任一文件缺失或无法读取，停止并询问
2. 设计最小 schema 变更（优先新增字段/表，避免破坏性修改）
3. 生成 Alembic 迁移并核对升级/回滚逻辑
4. 执行 `alembic upgrade head` 并进行插入/查询验证
5. 执行 `alembic downgrade -1`（或目标版本）并确认回滚有效
6. 输出变更清单与验证结果

## 护栏
- 改动最小化，禁止大幅调整数据库结构
- 必须提供 upgrade/downgrade 与插入/查询验证
- 若需要改目录结构、引入新依赖或破坏性迁移，先询问用户

## 验收命令
- `alembic upgrade head`
- `alembic downgrade -1`
- `python -m pytest -q`（若有迁移相关测试）
- `python scripts/<verify_db>.py` 或等价 SQL 验证命令

## 失败处理
- 迁移失败时，先说明失败点与影响范围，再给最小修复
- 若数据回滚不安全或不可逆，立刻停止并询问
- 环境缺失导致无法验证时，列出缺口并请求用户补充
