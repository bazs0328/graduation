---
name: learner-profile
description: 学习者画像落库与更新（ability/theta、frustration、weak_concepts）并输出 difficulty_plan；用于画像表结构/更新策略/查询接口调整时。
---

# learner-profile

## 目标
- 画像落库可查
- 最小字段完整：ability_level 或 theta、frustration_score、weak_concepts
- 输出 difficulty_plan 供 quiz-engine 使用

## 触发条件
- 新增/修改 learner_profile 表或更新逻辑
- 需要输出 difficulty_plan 或画像查询

## 输入
- 用户标识（session/user）
- 测验结果与学习记录
- 画像字段约束

## 输出
- 画像表结构/更新逻辑说明
- difficulty_plan 生成说明或示例
- 数据库查询/验证命令

## 步骤
1. 读取并理解：ai-docs/PROJECT.md、ai-docs/AGENTS.md、ai-docs/CONTEXT.md、ai-docs/CURRENT.md、ai-docs/TASKS.md；若任一文件缺失或无法读取，停止并询问
2. 设计最小字段并确认落库方式
3. 实现画像更新（基于测验/学习记录）
4. 生成 difficulty_plan 并对接 quiz-engine
5. 提供查询验证与回归方式

## 护栏
- 画像必须落库可查，不得只保存在内存
- 一次只处理画像相关最小改动
- 必须给可复现验证（SQL/curl/scripts/pytest）
- 若需大幅改库或引入依赖，先询问

## 验收命令
- `python -m pytest -q`（若有画像测试）
- `mysql -e "SELECT ... FROM learner_profile WHERE ...;"`（或等价查询）
- `curl -X GET http://localhost:8000/profile/me`

## 失败处理
- 更新失败先定位最小修复点并说明影响
- 缺少用户标识或数据源时，暂停并询问
