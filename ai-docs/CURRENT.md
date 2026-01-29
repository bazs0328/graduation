# CURRENT.md
# 当前阶段说明（会频繁更新，以此为最高优先级）

## 阶段名称
Phase 5：DeepTutor 体验对齐与增强（Parity）

---

## 阶段目标（本阶段只做这些）

在保持 Phase 1/2/3/4 主链路稳定的前提下，对齐 DeepTutor 的核心体验：

1. 多代理解题与可追溯输出：引入“规划→求解→校验→格式化”的可视化链路，并保持引用可追溯
2. 互动可视化学习：将复杂概念拆解为步骤化、可视化的页面/流程，形成可操作的学习体验
3. 考试仿真与题型增强：支持“参考试卷风格”与多题型强化练习
4. 深度研究与 IdeaGen：提供可持续的研究/洞见生成链路，结构化产出与复盘
5. 知识系统化：个人知识库/Notebook/知识图谱/记忆系统的统一入口与可回访体验

---

## 本阶段交付重点（建议至少这些）

- 解题链路：多步骤推理过程可视化 + 引用/工具记录可回放
- 学习可视化：交互式页面或流程图驱动学习路径
- 题库/仿真：可上传参考试卷并生成风格一致的练习
- 深度研究：多阶段研究链路（计划→研究→报告）并落库
- 知识系统：知识库/Notebook/知识图谱统一入口与管理
- 验证：端到端流程可复现，重启后关键链路可用

---

## 继承约束（必须保持）

- 初级/低水平用户默认不出 Hard（Hard = 0），且 Easy 占比高（如 ≥80%）
- 若检测到“明显过难”（如前 5 题错 ≥ 4，或 accuracy < 阈值）：
  - 自动降档（Hard=0，Easy ↑）
  - 提供鼓励性反馈，并设置 next_quiz_recommendation
- 资料优先：题目与解析尽量基于资料片段（可用 chunk 引用）

---

## 本阶段禁止事项（非常重要）

- 引入复杂机器学习训练/微调
- 引入多角色权限系统（教师/管理员）
- 无限制工具调用（必须白名单 + 配额 + 可关闭）
- 大规模重构已稳定的上传/解析/索引/检索链路
- 同时推进多个大模块（一次只推进一个纵向切片）

---

## 本阶段完成标准（满足才进入下一阶段）

- 多代理解题链路可视化 + 产物可回访（含引用/工具轨迹）
- 互动可视化学习路径可用（至少 1 条端到端）
- 参考试卷仿真出题可用（风格/题型/难度）
- 深度研究链路与 IdeaGen 可用（结构化产出）
- 个人知识库 + Notebook + 知识图谱最小闭环
- README/脚本提供可复现步骤，smoke/pytest 通过
- 重启服务后关键链路仍可用（含检索）

---

## 阶段推进记录（门禁）

验收日期：2026-01-29
验收命令：
1) docker compose up -d --build backend
2) docker compose exec backend sh /app/scripts/dev_smoke.sh
3) docker compose exec backend pytest
4) docker compose exec backend alembic upgrade head
5) docker compose restart backend
6) python3 - <<'PY' ... POST /search 验证索引可用

关键输出摘要：
- dev_smoke.sh 覆盖 health/upload/index/chat/quiz/submit/profile/sources/quiz recent/research（2026-01-29）
- pytest 4 passed（2026-01-29）
- alembic upgrade head 通过（2026-01-29）
- 重启后 /search 返回结果，索引可用（2026-01-29）

验收日期：2026-01-26
验收命令：
1) docker compose up -d --build backend
2) docker compose exec backend sh /app/scripts/dev_smoke.sh
3) docker compose exec backend pytest
4) docker compose exec backend alembic upgrade head
5) docker compose restart backend
6) docker compose exec backend python - <<'PY' ... POST /search 验证索引可用

关键输出摘要：
- dev_smoke.sh 覆盖 health/upload/index/chat/quiz/submit/profile/sources/quiz recent（2026-01-26）
- pytest 4 passed（2026-01-26）
- alembic upgrade head 通过（2026-01-26）
- 重启后 /search 返回结果，索引可用（2026-01-26）
