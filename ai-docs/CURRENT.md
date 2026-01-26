# CURRENT.md
# 当前阶段说明（会频繁更新，以此为最高优先级）

## 阶段名称
Phase 4：突破对齐与产品化（Breakthrough）

---

## 阶段目标（本阶段只做这些）

在保持 Phase 1/2/3 主链路稳定的前提下，做出“突破级”体验提升：

1. 工具与推理突破：引入受控工具调用（Web 搜索/代码执行/外部工具白名单），并保证引用可追溯
2. 研究与笔记：提供研究/Notebook 流程，把“资料→推理→结论→笔记”串成可复盘产物
3. 学习体验跃迁：仪表盘详情 + 学习路径增强 + 题目质量提升（更像真实学习产品）
4. 可视化与交互：关键步骤可视化展示（流程/证据/推理），支持必要的 streaming
5. 交付与稳定性：端到端可复现、重启后关键链路可用（含检索）

---

## 本阶段交付重点（建议至少这些）

- 工具与推理：至少 1 个“可控工具链”完成端到端（搜索/执行/检索 -> 引用 -> 回答）
- 研究与笔记：Notebook/研究产物可保存、可回访
- 学习记录增强：仪表盘详情页、学习活动聚合（可复盘）
- 学习引导增强：路径更“可行动”，每一步有理由与来源
- 题目与解释：题型覆盖更合理、解析与引用更完整
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
- 无限制工具调用（必须白名单 + 配额 + 可关闭）
- 大规模重构已稳定的上传/解析/索引/检索链路
- 同时推进多个大模块（一次只推进一个纵向切片）

---

## 本阶段完成标准（满足才进入下一阶段）

- 至少 1 条“工具/研究”突破链路完成（含引用与可追溯产物）
- Notebook/研究产物可保存、可回访
- 学习记录与路径增强可用：仪表盘详情 + 路径清晰、可解释
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
