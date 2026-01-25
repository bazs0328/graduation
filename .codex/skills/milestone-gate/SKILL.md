---
name: milestone-gate
description: 里程碑门禁检查（dev_smoke/pytest/alembic upgrade/重启恢复与索引可用性）；用于判断“可推进/不可推进”并给出最小修复建议。
---

# milestone-gate

## 目标
- 执行里程碑门禁检查并给出明确结论
- 结论必须基于命令结果
- 失败时提供最小修复建议

## 触发条件
- 用户要求里程碑验收/上线门禁/是否可推进
- 需要运行 smoke/pytest/迁移/重启恢复检查

## 输入
- 当前分支代码
- 已配置的脚本/服务启动方式
- 目标里程碑说明（若有）

## 输出
- 门禁检查结果清单（每条含命令与结果）
- “可推进/不可推进”结论
- 失败项的最小修复建议
- 验证命令列表

## 步骤
1. 读取并理解：ai-docs/PROJECT.md、ai-docs/AGENTS.md、ai-docs/CONTEXT.md、ai-docs/CURRENT.md、ai-docs/TASKS.md；若任一文件缺失或无法读取，停止并询问
2. 确认服务启动/重启方式（README 或 scripts）；若未知，先询问
3. 依次执行门禁命令并记录结果：dev_smoke → pytest → alembic upgrade head → 服务重启 → 索引可用性验证
4. 若任一关键门禁失败，标记“不可推进”，并给出最小修复建议
5. 全部通过后，标记“可推进”，并保留证据摘要

## 护栏
- 一次只做门禁验证，不擅自改业务逻辑
- 结论必须基于命令输出，不可主观判断
- 改动最小化，如需改目录结构或引入依赖先询问
- 必须给可复现验证命令与结果摘要

## 验收命令
- `bash scripts/dev_smoke.sh`
- `pytest -q`
- `alembic upgrade head`
- `docker compose restart <service>` 或 README 中定义的重启命令
- 索引可用性验证：`curl -X .../search` 或项目已有的检索验证脚本

## 失败处理
- 明确指出失败命令与日志片段
- 提供最小修复路径（限定影响范围）
- 若无法确认重启/索引验证方式，暂停并询问
