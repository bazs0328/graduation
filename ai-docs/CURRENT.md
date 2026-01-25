# CURRENT.md
# 当前阶段说明（会频繁更新，以此为最高优先级）

## 阶段名称
Phase 2：学习记录 + 用户画像（MVP）+ 自适应测验闭环（Quiz MVP）

---

## 阶段目标（本阶段只做这些）

在保持 Phase 1 主链路稳定的前提下，新增并打通“测验闭环”：

1. 学习记录可用：记录问答与测验行为（最小必要字段）
2. 用户画像（MVP）可用：能驱动“难度控制”和“错题优先”
3. 测验生成可用：基于资料内容生成题目（单选/判断/简答），并带难度标签（Easy/Medium/Hard）
4. 难度自适应可用：根据画像决定难度配比，避免“基础差却出难题打击信心”
5. 过难回调可用：测验进行中/提交后发现明显过难时自动降档并给出正向反馈
6. API 行为稳定、可复现：提供脚本/README 可一键验证测验闭环

---

## 本阶段交付接口（建议至少这些）

- POST `/quiz/generate`
  - 输入：document_id（或范围）、题量、题型、可选 focus_concepts
  - 输出：题目列表（结构化 JSON）、每题 difficulty、reference_chunks（可选）

- POST `/quiz/submit`
  - 输入：quiz_id、用户答案
  - 输出：得分/正确率、每题判定、简要反馈、画像更新摘要（可选）

- GET `/profile/me`（模拟登录/会话下）
  - 输出：ability_level 或 theta、frustration_score、top_weak_concepts、最近测验摘要

- （可选）GET `/quiz/{quiz_id}`（便于回看与调试）

---

## 本阶段最小数据集（允许先简后全）

新增表（或等价结构）建议最小包含：

- `quizzes`
  - id, user_id/session_id, document_id, created_at, difficulty_plan_json

- `quiz_questions`
  - id, quiz_id, type, difficulty, stem, options_json, answer_json, explanation, related_concept, source_chunk_ids_json

- `quiz_attempts`（或合并到 quizzes）
  - quiz_id, submitted_at, score, accuracy, summary_json

- `concept_stats`
  - user_id/session_id, concept, correct_count, wrong_count, last_seen

- `learner_profile`
  - user_id/session_id, ability_level 或 theta, frustration_score, last_updated

> 备注：用户标识沿用 Phase 1 的模拟登录/会话体系，不引入复杂鉴权。

---

## 本阶段个性化要求（硬性约束）

系统必须做到以下行为（否则判定 Phase 2 不合格）：

1. 初级/低水平用户默认不出 Hard（Hard = 0），且 Easy 占比高（如 ≥80%）
2. 错题知识点优先，但仍受难度配比约束（不能“错得多就狂上难题”）
3. 若检测到“明显过难”（如前 5 题错 ≥ 4，或 accuracy < 某阈值）：
   - 自动降档（Hard=0，Easy ↑）
   - 提供“回血题”或鼓励性反馈
4. 资料优先：测验题与解析必须尽量基于资料片段（可用 chunk 引用辅助）

---

## 本阶段推荐实现顺序（必须纵向切片）

1) 先做数据表 + `/quiz/generate` 只生成 Easy（跑通）
2) 再做 `/quiz/submit` + 记录 attempts（跑通）
3) 再做 concept_stats 更新（错题优先可用）
4) 再做 learner_profile（ability_level / frustration_score）
5) 最后加难度配比 + 过难回调 + 正向反馈

每完成一步都要有可复现的 curl 或脚本验证。

---

## 本阶段禁止事项（非常重要）

在 Phase 2 禁止做：

- 引入复杂机器学习训练/微调
- 引入多角色权限系统（教师/管理员）
- 追求高并发、缓存体系、性能优化（除非出现明显阻塞）
- 大规模重构 Phase 1 已稳定的上传/解析/索引/检索链路
- 同时推进多个大模块（一次只推进一个纵向切片）

---

## 本阶段完成标准（满足才进入下一阶段）

当且仅当以下条件全部满足，Phase 2 完成：

- `/quiz/generate` 与 `/quiz/submit` 可连续稳定运行，题目结构化输出正确
- 画像确实影响出题：同一资料下，不同画像能产生不同难度配比结果
- “基础差不出难题”与“过难回调”可通过脚本复现验证
- 学习记录与画像更新可在数据库中查询到（非仅内存）
- README 或 scripts 提供一键 smoke 流程：上传资料→建索引→问答→生成测验→提交→查看画像

---

## 下一阶段预告（仅提示，不在本阶段实现）

Phase 3 方向（不承诺实现顺序）：
- 摘要生成/结构化知识点（更强资料理解）
- 真实 Embedding/真实 LLM 接入与可配置切换
- 更细粒度概念体系与学习路径推荐