---
name: task-cycle
description: 全自动任务循环：从 ai-docs/TASKS.md 获取第一条未完成任务→创建分支→实现任务→门禁验证→更新 TASKS 状态→输出交付摘要并等待验收；验收通过后执行 merge_task 合并清理。
---

# task-cycle

## 目标
- 自动推进单条任务闭环（从 TASKS 取任务到门禁验证与状态更新）
- 交付结果可复现、可验收、可回滚
- 验收后可执行合并清理子流程

## 触发条件
- 用户要求“自动执行下一条任务/任务循环/全自动推进”
- 用户要求“自动追加任务/分析并追加到 Backlog”
- 需要包含分支、门禁验证、TASKS 状态更新的完整流程
- 需要在验收后合并分支

## 输入
- 必读文档：ai-docs/CURRENT.md、PROJECT.md、AGENTS.md、CONTEXT.md、TASKS.md、PROMPTS.md（若存在）
- 当前仓库与 git 状态
- run_next_task / analyze_and_append / merge_task 的参数（若提供）

## 输出
- 计划输出（改代码前）
- 变更文件清单与验证结果
- TASKS 状态更新与验证方式记录
- Backlog 追加任务记录（若执行 analyze_and_append）
- 固定格式交付摘要（并等待用户验收）

## 步骤
1. 运行前必读并遵守：ai-docs/CURRENT.md（最高优先级）、PROJECT.md、AGENTS.md、CONTEXT.md、TASKS.md、PROMPTS.md（如存在）
2. 若缺失 CURRENT.md 或 TASKS.md：停止并提示用户补齐
3. 若 CURRENT.md 与 TASKS 冲突：以 CURRENT.md 为准并暂停询问
4. 根据用户选择进入子流程：run_next_task（默认）/ analyze_and_append / merge_task

## 子流程：run_next_task（默认）

### 两段式流程（新增）
- 阶段一（计划，默认）：仅生成计划输出，不创建分支、不修改代码、不更新 TASKS 状态；若 create-plan 可用必须先调用它，再补齐本技能要求的计划项。
- 阶段二（执行）：仅在用户明确“确认执行”后进入；按下文分支/实现/验证/TASKS 更新流程实施。

### 参数（可选，含默认）
- stage：默认 "plan"，可选 "execute"（仅在 execute 或用户明确“确认执行”后才允许实施）
- main_branch：默认 "main"
- branch_mode：默认 "feat"（bug 修复可用 "fix"，文档可用 "chore"）
- stop_after_done：默认 true
- require_smoke：默认 true（若存在 scripts/dev_smoke.sh 必跑）
- require_pytest：默认 false（存在就跑，但不强制）
- allow_schema_change：默认 false（如为 true，必须强调升级/回滚验证）
- task_id：可选；未提供则从 TASKS.md 取第一条 [ ] 未开始

### 用法示例
- 计划阶段（默认）：用户说“请运行 run_next_task 生成计划”→ 只输出计划并等待你回复“确认执行”
- 执行阶段：用户说“确认执行 run_next_task”或“run_next_task stage=execute”→ 进入实施流程

### 任务选择规则（强制）
- 只允许选择 TASKS.md 中第一条 [ ] 未开始 的任务
- 选中后立刻将该条标记为 [~] 进行中
- 若已存在 [~] 进行中任务：默认继续该任务，除非用户明确要求重置

### 分支规则（强制）
- 禁止在 main_branch 上开发
- 分支命名：<branch_mode>/<task_id>-<short_slug>
- short_slug 从任务标题提取（短英文或拼音均可）
- 开始前必须 git pull 更新 main_branch
- 创建分支后必须确认当前分支不等于 main_branch

### 计划输出（改代码前必须输出）
- 任务 ID 与标题
- 将修改/新增的文件清单（尽量短）
- 将运行的验证命令（至少 2 条）
- 回滚方式（如何撤销分支/回退到 main）

### 实现约束（强制）
- 只做这一条任务，不做额外需求
- 改动最小化：优先新增文件，不重构无关模块
- 业务逻辑放 services，路由只做编排
- 不新增依赖/不改目录结构（除非任务明确要求且先说明）

### 提交规则（强制）
- 至少 2 个 commit，最多 6 个 commit
- commit message 格式：type(scope): desc
- 完成后必须停止等待验收（stop_after_done=true）

### 门禁验证（强制）
- 若存在 scripts/dev_smoke.sh：必须运行并贴关键输出摘要
- 若涉及迁移：必须运行 alembic upgrade head，并尽量提供 downgrade 说明
- 其余验证：pytest（若存在）、关键 curl 示例
- 门禁失败：不得标记任务完成，必须修复或报告阻塞点

### TASKS 状态更新（强制）
- 门禁通过后，将任务从 [~] 改为 [x]
- 在任务条目下追加“验证方式/命令”（或确保 README/scripts 已包含）

### 交付摘要输出（固定格式，必须停止等待验收）
- 已完成任务：<task_id>
- 分支：<branch>
- 变更概览：<关键文件清单>
- 验证命令：
  1) ...
  2) ...
- 关键输出摘要：<简短>
- 验收对照表：逐条对照该任务验收项（是/否 + 证据）
- 等待用户验收：说明用户要跑哪些命令

## 子流程：analyze_and_append

### 触发条件（强制）
- 满足“自动追加任务策略”（以 CURRENT.md / PROMPTS.md 为准）；若不满足，停止并说明原因
- 用户明确要求“自动追加任务/分析并追加到 Backlog”

### 分析范围（强制）
- 必读：ai-docs/CURRENT.md、ai-docs/TASKS.md
- 仓库现状：是否已有 frontend 目录；是否已接真实 LLM（配置/客户端/调用链路等）
- 需要给出最小证据（目录/文件名或配置片段位置）

### 输出与写入（强制）
- 仅追加到 TASKS.md 的【Backlog / 待规划】区域，不改动其他任务
- 任务编号格式：FE-### / LLM-### / REL-###（按类别递增，3 位数字）
- 每条任务必须包含以下字段：
  - 目标：
  - 交付物：
  - 验收：
  - 依赖：
  - 风险回滚：

### 追加后动作
- 追加完成后必须停止，等待用户确认是否开始执行（不得自动进入 run_next_task）

### 用法示例
- 用户说“请执行 analyze_and_append”→ 追加到 Backlog 并等待确认

## 子流程：merge_task

### 输入
- branch：要合并的分支名（必填）
- main_branch：默认 "main"
- delete_branch：默认 true
- merge_strategy：默认 "--no-ff"

### 合并步骤（强制）
1. 切到 main_branch 并 git pull
2. git merge --no-ff <branch>
3. 推送（如存在远端）
4. 合并后建议跑一次 smoke（若存在）
5. delete_branch=true 时删除本地分支

### 输出（强制）
- 合并命令执行情况
- 合并后 smoke/验证情况（如执行）
- 下一步建议：继续 run_next_task 或等待新任务

## 护栏
- 禁止在 main_branch 开发
- 禁止一次做多个任务
- 禁止缺少可复现验证
- 新增依赖/大改 schema/改目录结构/大重构：必须先询问
- CURRENT.md 与 TASKS 冲突时必须暂停并询问

## 验收命令
- `bash scripts/dev_smoke.sh`
- `pytest -q`
- `alembic upgrade head`
- `git status --short`

## 失败处理
- 若缺失必读文件（CURRENT/TASKS）：停止并提示用户补齐
- 门禁失败：输出失败命令与关键日志，给出最小修复建议
- 若无法继续（环境/权限/依赖不足）：明确阻塞点并等待用户指示
