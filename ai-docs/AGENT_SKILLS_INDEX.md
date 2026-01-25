# AGENT_SKILLS_INDEX.md
# Agent Skills 索引与使用说明

## 使用约定（统一）
- 每次执行任务前必须阅读：ai-docs/PROJECT.md、ai-docs/AGENTS.md、ai-docs/CONTEXT.md、ai-docs/CURRENT.md、ai-docs/TASKS.md
- 以 ai-docs/CURRENT.md 为最高优先级
- 一次只做一件事、改动最小化、必须给可复现验证（curl/scripts/pytest）
- 若前置文档缺失（例如 TASKS.md），先询问用户再继续

## 已安装技能（全局）
- `create-plan`：已安装（C:\Users\bazs0\.codex\skills\create-plan）。若未生效，请重启 Codex 后确认出现 `$create-plan`
- `gh-fix-ci`：已安装（C:\Users\bazs0\.codex\skills\gh-fix-ci）
- `gh-address-comments`：已安装（C:\Users\bazs0\.codex\skills\gh-address-comments）

## 仓库技能（repo-scoped：.codex/skills/）

### task-runner
- 用途：从 TASKS.md 取第一条未完成任务 → 计划 → 实施 → 验收对照
- 调用：`$task-runner`
- 何时用：推进单条任务或需要变更清单+验证命令时
- 验收命令：`bash scripts/dev_smoke.sh`（或 `pytest -q`）

### milestone-gate
- 用途：里程碑门禁检查（smoke/pytest/迁移/重启恢复/索引可用）并给出可推进结论
- 调用：`$milestone-gate`
- 何时用：上线或阶段验收前
- 验收命令：`bash scripts/dev_smoke.sh`、`pytest -q`、`alembic upgrade head`

### db-migrate
- 用途：最小 schema 迁移与 upgrade/downgrade、插入查询验证
- 调用：`$db-migrate`
- 何时用：新增字段/轻量结构调整
- 验收命令：`alembic upgrade head`、`alembic downgrade -1`

### api-contract
- 用途：接口契约（输入/输出 JSON、统一错误结构、409 前置条件不足、curl 示例）
- 调用：`$api-contract`
- 何时用：新增或变更 API
- 验收命令：`curl -X POST http://localhost:8000/<path> -H "Content-Type: application/json" -d '<json>'`

### quiz-engine
- 用途：测验生成/提交规则、难度控制、过难回调、资料可追溯
- 调用：`$quiz-engine`
- 何时用：修改测验逻辑或难度策略
- 验收命令：`curl -X POST http://localhost:8000/quiz/generate -H "Content-Type: application/json" -d '<json>'`

### learner-profile
- 用途：画像落库与更新，输出 difficulty_plan
- 调用：`$learner-profile`
- 何时用：画像字段/更新逻辑调整
- 验收命令：`curl -X GET http://localhost:8000/profile/me`

### smoke-maintainer
- 用途：维护 scripts/dev_smoke.sh，新接口必须进 smoke，失败需日志与退出码
- 调用：`$smoke-maintainer`
- 何时用：新增关键接口或 smoke 失效
- 验收命令：`bash scripts/dev_smoke.sh`

### bug-triage
- 用途：Bug 复现→根因证据→最小修复→回归验证
- 调用：`$bug-triage`
- 何时用：处理用户报 bug 或回归问题
- 验收命令：`pytest -q`
