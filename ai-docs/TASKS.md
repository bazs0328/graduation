# TASKS.md
# 任务队列（Codex 执行用，长期有效）

> 本文件是 Codex 的“工作队列”。Codex 每次启动都应从这里找下一条未完成任务执行。
> 规则：一次只做一条任务，完成后必须更新状态并给出可复现验证方式。

## 自动追加任务策略（Agent 必须遵守）

当满足以下任一条件时，允许 Agent 自动分析仓库与 CURRENT/TASKS，并在 TASKS.md 末尾“追加”新任务：
- 任务队列剩余未完成任务 <= 3 条
- 刚完成一个里程碑（里程碑验收记录写完）
- 用户明确说“准备转前端/接真实LLM/准备交付”

追加规则（强制）：
1) 只能“追加”到 TASKS.md 的【Backlog / 待规划】区域，不得插队改顺序（除非用户明确要求重排）
2) 必须按类别与前缀命名，例如：
   - FE-xxx：前端
   - LLM-xxx：真实 LLM 接入
   - REL-xxx：交付/部署/稳定性
3) 每条新增任务必须包含：
   - 目标
   - 交付物（文件/接口/脚本）
   - 验收标准（可复现命令/步骤）
   - 依赖（必须先完成哪些任务）
   - 风险与回滚
4) 新增任务后必须停止并提示用户“已追加任务，是否开始执行下一条”
5) 不允许因为追加任务而改变技术选型；如需新增依赖/外部服务，必须先提案

## 里程碑划分与门禁（强制）

本项目按“里程碑”推进。Agent 不需要猜测里程碑：必须严格按下表与完成标准判断。

### 里程碑列表
- Milestone A（后端测验闭环）：覆盖 P2-001 ~ P2-009
- Milestone B（前端 MVP）：覆盖 FE-001 ~ FE-006（后续会在 TASKS 中追加）
- Milestone C（稳定性与交付）：覆盖 REL-001 ~ REL-xxx（后续会在 TASKS 中追加）

### 里程碑完成标准（只有满足才允许进入下一里程碑的任务）
每个里程碑完成前，必须通过门禁：
1) scripts/dev_smoke.sh 通过（若存在，优先）
2) pytest 通过（若存在）
3) 若本里程碑包含迁移：alembic upgrade head 通过
4) 重启服务后关键链路仍可用（至少：health + 本里程碑主链路）

### 里程碑推进规则
- Agent 在完成某里程碑的最后一个任务后，必须：
  1) 运行门禁并记录结果
  2) 在 TASKS.md 中为该里程碑写一段“里程碑验收记录”（命令 + 关键输出摘要）
  3) 然后才可以开始下一里程碑的任务
- 未通过门禁不得推进里程碑，也不得更新 CURRENT.md 表示“已完成”。

### 里程碑验收记录模板（必须照填）
里程碑：Milestone X
验收日期：YYYY-MM-DD
验收命令：
1) ...
2) ...
关键输出摘要：
- ...
结论：通过 / 不通过
阻塞点（如有）：
- ...


---

## 一、全局执行规则（必须遵守）

1) 一次只做一个任务 ID（禁止并行推进多个任务）
2) 必须先读：ai-docs/PROJECT.md / AGENTS.md / CONTEXT.md / CURRENT.md / TASKS.md
3) 必须“纵向切片”：先打通一条链路再扩展
4) 必须最小改动：禁止无关重构；优先新增文件而不是重写
5) 必须可复现：每个任务都要给出验证命令（curl / scripts / pytest）
6) 必须更新至少其一：README 或 scripts（推荐 scripts/dev_smoke.sh）
7) 如需新增依赖、重大 schema 改动、改变目录结构：必须先提出并等待确认

---

## 二、统一验收标准（适用于所有任务）

每条任务结束时，必须输出“验收对照表”，逐条回答：
- 本任务目标是否完成（是/否）
- 哪些文件被修改/新增
- 跑了哪些命令验证（含关键输出摘要）
- 已更新哪些 README/scripts
- 已知风险/后续建议（如有）

---

## 三、任务状态标记方式（简单且稳定）
- [ ] 未开始
- [~] 进行中（仅 Codex 使用，避免重复开工）
- [x] 已完成（必须附上验证方式/命令）

---

## 四、当前任务队列（从上到下执行）

### [x] P2-001 数据库：测验与画像最小表 + Alembic 迁移
**目标**
引入最小可用的“测验闭环 + 用户画像”持久化结构。

**交付**
- 新增/更新表（可按你的现有命名微调，但语义必须一致）：
  - quizzes（一次测验的元信息）
  - quiz_questions（测验题目）
  - quiz_submissions 或 quiz_attempts（提交与得分）
  - concept_stats（按知识点累计对错）
  - learner_profile（画像：ability/frustration 等）
- SQLAlchemy models + Pydantic schemas
- Alembic migration：upgrade/downgrade 可用

**约束**
- 向后兼容优先（能新增不删除）
- 不破坏 Phase 1 稳定链路

**验收**
- docker compose exec backend alembic upgrade head 成功
- 能插入并查询一条 quiz + question + profile（脚本或临时验证代码均可）
- README 增加迁移命令与验证方法

**验证方式**
- docker compose exec backend alembic upgrade head
- docker compose exec backend python /app/scripts/verify_quiz_schema.py

**关键输出摘要**
- 用户确认上述命令已跑通（2026-01-25）

---

### [x] P2-002 接口：/profile/me（MVP）
**目标**
提供当前用户画像查询（即使是默认值也必须落库可查）。

**交付**
- GET /profile/me
- 返回字段（最小）：
  - ability_level（初级/中级/高级）或 theta（浮点，二选一）
  - frustration_score（整数或浮点，>=0）
  - weak_concepts（数组：[{concept, wrong_count, wrong_rate}] 或简单字符串数组）
  - last_quiz_summary（可选）

**验收**
- 新用户首次访问返回默认画像，并确保 learner_profile 表中有记录
- curl 示例写入 README 或 scripts
- /profile/me 返回结构稳定（字段不缺）

**验证方式**
- docker compose exec backend alembic upgrade head
- curl http://localhost:8000/profile/me
- docker compose exec backend python -c "from app.db.session import SessionLocal; from app.db import models; db=SessionLocal(); print(db.query(models.LearnerProfile).count()); db.close()"

**关键输出摘要**
- /profile/me 返回 {"ability_level":"beginner","frustration_score":0,"weak_concepts":[],"last_quiz_summary":null}
- learner_profile 记录数 >= 1（2026-01-25）

---

### [x] P2-003 接口：/quiz/generate（先 Easy-only 跑通）
**目标**
打通测验生成链路：检索资料片段 → 生成题目（只生成 Easy）→ 落库 → 返回结构化 JSON。

**输入建议**
- document_id（或 doc_ids）
- count（题量）
- types（["single","judge","short"]）

**交付**
- POST /quiz/generate
- 输出：quiz_id + questions[]
- questions[] 每题必须包含：
  - question_id, type, difficulty="Easy"
  - stem
  - options（仅 single 需要）
  - answer（结构化：single 为选项标识，judge 为 true/false，short 为参考要点/参考答案）
  - explanation（基于资料片段的解析/要点）
  - source_chunk_ids（至少 1 个）
  - related_concept（先用简单规则即可，如由 chunk 元数据/标题推断）

**硬约束**
- 必须“资料优先”：题目必须基于检索到的 chunk；若检索为空，返回 409 并提示“资料不足/索引未建”
- 输出必须是结构化字段齐全（缺字段视为失败）
- 允许沿用 Phase 1 的 MockLLM（本任务不强制接外部 LLM）

**验收**
- 用 sample.md 生成至少 5 题 Easy（可多次调用覆盖题型）
- quizzes 与 quiz_questions 落库可查
- scripts/dev_smoke.sh 增加生成测验步骤（或新增 smoke 脚本）


**????**
- docker compose exec backend alembic upgrade head
- docker compose exec backend sh /app/scripts/dev_smoke.sh

**??????**
- dev_smoke.sh ?? quiz_id ? questions?Easy-only?>=5 ???2026-01-25?
---

### [x] P2-004 接口：/quiz/submit（评分 + 提交记录落库）
**目标**
提交答案 → 对客观题判分 → 简答题给参考答案/要点（不强制自动评分）→ 落库 submission/attempt。

**交付**
- POST /quiz/submit
- 输入：quiz_id + answers（按 question_id）
- 输出：
  - score（数值）
  - accuracy（0~1）
  - per_question_result[]：question_id, correct, expected_answer, user_answer
  - feedback_text（简短反馈）

**验收**
- 单选/判断正确判分
- 简答题不强行判对错，至少返回参考答案/要点与自评提示
- 提交记录落库可查
- scripts/dev_smoke.sh 增加：生成→提交→输出结果

**????**
- docker compose exec backend alembic upgrade head
- docker compose exec backend sh /app/scripts/dev_smoke.sh
- docker compose exec backend pytest

---

### [ ] P2-005 concept_stats 更新（错题优先基础）
**目标**
提交测验时按 related_concept 更新 concept_stats，并能输出弱项概念。

**交付**
- /quiz/submit 中更新 concept_stats：
  - correct_count / wrong_count / last_seen
- /profile/me 返回 weak_concepts（按 wrong_count 或 wrong_rate 排序）

**验收**
- 连续提交后 concept_stats 随之变化
- /profile/me 可看到弱项概念列表（至少能出现 1 条）

---

### [ ] P2-006 画像更新（MVP）：ability_level + frustration_score
**目标**
实现最小可用画像更新，能驱动难度控制与“信心保护”。

**建议实现（先稳后准）**
- ability_level：最近 N 道客观题正确率分档
  - 初级 <50%，中级 50~80%，高级 >=80%
- frustration_score：
  - 单次 accuracy 很低或连续错题 → 上升
  - 表现好 → 缓慢下降（每次提交 -1，最小 0）

**验收**
- 两个不同用户/会话在多次提交后画像会分化
- frustration_score 在连续低分时上升并可在 /profile/me 体现

---

### [ ] P2-007 难度控制：/quiz/generate 根据画像决定 difficulty_plan
**目标**
让测验生成真正“因人而异”：根据 learner_profile 输出难度配比并按 plan 生成（引入 Medium/Hard）。

**硬规则（必须实现）**
- 初级或 frustration_score 高：Hard=0 且 Easy>=80%
- 中级：Easy≈50% + Medium≈50%（Hard 可先 0 或 <=10%）
- 高级：Easy≈20% + Medium≈60% + Hard≈20%
- 错题优先（weak_concepts）但不得突破难度约束

**交付**
- /quiz/generate 返回 difficulty_plan（写入 quizzes.difficulty_plan_json）
- quiz_questions.difficulty 按 plan 分配

**验收**
- 构造两个画像（初级 vs 高级）在同一资料下生成测验，difficulty_plan 明显不同
- 初级用户 Hard 数量为 0（可脚本验证）

---

### [ ] P2-008 过难回调（防翻车体验）
**目标**
当测验明显过难时自动“降档 + 鼓励反馈 + 下次推荐更保守”。

**最小策略（至少实现一种）**
- 提交后判断：
  - accuracy < 30% 或 前 5 题错 >= 4（客观题）→
    - frustration_score 上升
    - feedback_text 包含鼓励 + 具体建议（先复习哪一块）
    - 设置 next_quiz_recommendation = "easy_first"
- 下一次 generate：如果 recommendation 为 easy_first 或 frustration 高，plan 自动保守

**验收**
- 故意全错提交 → 触发回调（脚本可复现）
- 下次生成难度更保守（Hard=0，Easy 上升）

---

### [ ] P2-009 一键闭环：更新 scripts/dev_smoke.sh（端到端）
**目标**
你只靠脚本就能验收，无需手点接口。

**交付**
- scripts/dev_smoke.sh 覆盖：
  - /health
  - 上传 sample.md
  - /index/rebuild
  - /chat（问一个资料内问题）
  - /quiz/generate（至少 5 题）
  - /quiz/submit（包含“故意错”的用例）
  - /profile/me（展示画像变化与推荐）
- README 增加 Phase 2 验收步骤（复制命令即可跑）

**验收**
- 你本地执行 dev_smoke.sh 全通过（或明确失败点）
- 输出包含：quiz_id、score/accuracy、profile 关键字段变化、difficulty_plan

---

## 五、后续（可选增强任务，完成当前队列后再添加）
- ability_level → theta（Elo/IRT-lite）能力估计
- 更细粒度 concept 体系（章节/小节映射）
- 题目生成更严格的 schema 校验与回退策略

## Backlog / 待规划（允许自动追加）
> 这里的任务默认不自动执行，除非用户确认或被提升到“当前任务队列”。
