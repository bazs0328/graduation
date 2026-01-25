---
name: smoke-maintainer
description: 维护 scripts/dev_smoke.sh，新增关键接口必须加入 smoke，确保失败有明确退出码与日志；用于维护或扩展 smoke 流程时。
---

# smoke-maintainer

## 目标
- 维护 scripts/dev_smoke.sh 的可复现性
- 新增关键接口必须加入 smoke
- 失败时有明确退出码与日志

## 触发条件
- 新增/变更关键接口或流程
- 需要更新 smoke 验证脚本

## 输入
- 当前 smoke 脚本内容
- 新增接口或关键链路说明
- 期望的成功/失败标准

## 输出
- 更新后的 scripts/dev_smoke.sh
- 新增/调整的 smoke 项清单
- 运行结果与验证命令

## 步骤
1. 读取并理解：ai-docs/PROJECT.md、ai-docs/AGENTS.md、ai-docs/CONTEXT.md、ai-docs/CURRENT.md、ai-docs/TASKS.md；若任一文件缺失或无法读取，停止并询问
2. 审阅 scripts/dev_smoke.sh，定位新增关键接口的插入位置
3. 追加最小 smoke 步骤（含 curl/检查），保持可读性
4. 确保失败有明确退出码与日志输出
5. 运行 smoke 并记录结果

## 护栏
- 仅维护 smoke 脚本，不擅自改业务逻辑
- 新增关键接口必须进入 smoke
- 必须给出可复现验证命令与日志位置
- 改动最小化，必要时先询问用户

## 验收命令
- `bash scripts/dev_smoke.sh`

## 失败处理
- 输出失败步骤与日志片段
- 提供最小修复建议或回滚方式
- 若脚本运行环境不明确，先询问
