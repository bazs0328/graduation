# CURRENT.md
# 当前阶段说明（会频繁更新，以此为最高优先级）

## 阶段名称
Phase 3：前端 MVP + 可配置真实 LLM/Embedding + 交付与稳定性

---

## 阶段目标（本阶段只做这些）

在保持 Phase 1/2 主链路稳定的前提下，补齐可用的前端与可配置接入：

1. 前端 MVP 可用：上传/建索引/问答/测验生成与提交/画像查看可完整操作
2. 前后端契约稳定：核心接口的输入/输出结构清晰、错误提示可理解
3. 真实 LLM/Embedding 可配置：支持切换真实 provider 与 Mock/Hash 兜底
4. 交付与稳定性：一键启动、README/脚本可复现、重启后关键链路可用

---

## 本阶段交付重点（建议至少这些）

- 前端页面/流程：上传资料、索引重建、问答、测验生成与提交、画像查看
- 配置与说明：LLM/Embedding provider 配置开关与 README 说明
- 验证：前端端到端流程可复现（不依赖手工 curl）

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
- 大规模重构已稳定的上传/解析/索引/检索链路
- 同时推进多个大模块（一次只推进一个纵向切片）

---

## 本阶段完成标准（满足才进入下一阶段）

- 前端 MVP 可完整走通闭环（上传→索引→问答→测验生成/提交→画像）
- 真实 LLM/Embedding 可配置切换可用，Mock/Hash 兜底仍可运行
- README/脚本提供可复现步骤，smoke/pytest 通过
- 重启服务后关键链路仍可用

---

## 阶段推进记录（门禁）

验收日期：2026-01-25
验收命令：
1) docker compose up -d --build backend
2) docker compose exec backend alembic upgrade head
3) docker compose exec backend sh /app/scripts/dev_smoke.sh
4) docker compose exec backend pytest

关键输出摘要：
- dev_smoke.sh 覆盖 health/upload/index/chat/quiz/submit/profile，输出 quiz_id/score/accuracy/difficulty_plan/profile 字段（2026-01-25）
- alembic upgrade head 通过（2026-01-25）
- pytest 4 passed（2026-01-25）
