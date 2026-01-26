# CURRENT.md
# 当前阶段说明（会频繁更新，以此为最高优先级）

## 阶段名称
Phase 4：体验对齐与产品化（Lite）

---

## 阶段目标（本阶段只做这些）

在保持 Phase 1/2/3 主链路稳定的前提下，进一步对齐目标产品体验：

1. 体验对齐：仪表盘详情/学习记录聚合/学习路径增强，让用户完成闭环后有清晰下一步
2. 资料管理增强：多文档组织（集合/标签/最近使用）以支撑更长周期学习
3. 题目质量与可解释：题型覆盖更合理、解析与引用更完整
4. 交付与稳定性：端到端可复现、重启后关键链路可用（含检索）

---

## 本阶段交付重点（建议至少这些）

- 学习记录增强：仪表盘详情页、学习活动聚合（最小版）
- 学习引导增强：学习路径质量提升，清晰来源与下一步动作
- 资料组织：多文档集合/标签/最近使用（最小可用）
- 题目与解释：题型覆盖/解析可追溯（引用更完整）
- 验证：端到端流程可复现，重启后检索可用

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
- 多 Agent 双循环、深度研究、Web 搜索、代码执行等重型能力（除非明确授权）
- 大规模重构已稳定的上传/解析/索引/检索链路
- 同时推进多个大模块（一次只推进一个纵向切片）

---

## 本阶段完成标准（满足才进入下一阶段）

- 学习记录与路径增强可用：仪表盘详情 + 路径清晰、可解释
- 资料组织能力具备最小可用（集合/标签/最近使用）
- 题目生成与解析质量提升且可追溯
- README/脚本提供可复现步骤，smoke/pytest 通过
- 重启服务后关键链路仍可用（含检索）

---

## 阶段推进记录（门禁）

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
