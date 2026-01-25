---
name: quiz-engine
description: 测验引擎规则与实现约束（生成/提交/难度控制/过难回调/资料可追溯）；用于实现或修改测验逻辑、难度策略或出题规则时。
---

# quiz-engine

## 目标
- 生成/提交测验的核心流程可复现
- 难度控制与过难回调严格执行
- 题目可追溯到资料片段（source_chunk_ids）

## 触发条件
- 新增或修改测验生成/提交逻辑
- 调整难度配比、过难回调、或资料检索绑定规则

## 输入
- 学习者画像（ability/frustration/weak_concepts 或 difficulty_plan）
- 检索结果与资料片段
- 题型与题量需求

## 输出
- 可执行的测验生成/提交逻辑说明
- 强规则符合性说明
- 可复现验收脚本建议（curl 或 scripts）
- 变更文件清单

## 步骤
1. 读取并理解：ai-docs/PROJECT.md、ai-docs/AGENTS.md、ai-docs/CONTEXT.md、ai-docs/CURRENT.md、ai-docs/TASKS.md；若任一文件缺失或无法读取，停止并询问
2. 读取 learner_profile 或 difficulty_plan 作为难度配比依据
3. 执行检索；若无命中，返回 409 并说明资料不足
4. 生成题目并为每题绑定 source_chunk_ids
5. 应用硬规则：低水平/高 frustration 禁 Hard 且 Easy≥80%
6. 过难回调：accuracy<30% 或 前 5 题错≥4 → 降档 + 鼓励反馈 + next_quiz_recommendation
7. 输出验收脚本建议并补充 README/scripts

## 护栏
- 硬规则必须强制执行（以下任一违背即为错误）
  - 初级或高 frustration：Hard=0 且 Easy≥80%
  - 过难回调：accuracy<30% 或 前5题错≥4 → 降档 + 鼓励反馈 + next_quiz_recommendation
  - 无检索命中不生成题，返回 409
  - 每题必须绑定 source_chunk_ids
- 一次只修改测验相关单一链路，改动最小化
- 必须给可复现验证（curl/scripts/pytest）

## 验收命令
- `curl -X POST http://localhost:8000/quiz/generate -H "Content-Type: application/json" -d '<json>'`
- `curl -X POST http://localhost:8000/quiz/submit -H "Content-Type: application/json" -d '<json>'`
- `bash scripts/dev_smoke.sh`（若更新 smoke）

## 失败处理
- 若硬规则无法满足，停止并说明原因，询问用户
- 若检索为空，返回 409 并提示补充资料
- 验证失败时给出最小修复路径与回归方式
