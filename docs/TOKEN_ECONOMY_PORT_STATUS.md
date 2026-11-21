# Token Economy 移植 — Codex 侧实施状态（阶段 A，已完成并实测）

**日期**：2026-11-21。**执行者**：Codex（codex-cli 0.171.0）。
**范围**：仅 Codex 侧（交接文档 §4），阶段 A；Antigravity 侧（§5）按用户指示未动。
**规格**：`docs/TOKEN_ECONOMY_PORT.md`（ADR-032）。本文记录落地项、真实调用验证证据、剩余人工步骤。

## 1. 已落地项（每项均经真实调用验证）

| 项 | 位置 | 验证方式 | 结果 |
|---|---|---|---|
| 自动压缩阈值 180K | `~/.codex/config.toml` 顶层 `model_auto_compact_token_limit = 180000` | `codex doctor --json`：parse ok、未列入 unrecognized；外科手术式仅插入该键，其余逐字节不变（备份 `config.toml.bak-token-economy` 于同目录） | ✅ |
| 共享指令文件 | 仓库根 `AGENTS.md`（约 2.1KB，平铺无 frontmatter，Antigravity 亦可直接读） | `codex debug prompt-input`：token 规则全部出现在模型可见输入 | ✅ |
| 守卫② board-first | `.codex/hooks.json` PreToolUse `^view_image$` → `scripts/hooks/codex_token_guard.py` | 真实 exec 会话三次（末次不带绕过标志）：单图 view_image 被 deny，模型逐字收到理由且未重试 | ✅ |
| 守卫③ 150K 阶段提醒 | 同文件 PostModelRequest `.*`（检测）+ PreToolUse `^(Bash\|shell\|unified_exec)$`（注入） | 真实 exec 会话（`DRAMA_TOKEN_NUDGE_TOKENS=5000` 临时降阈）：模型逐字复述 `[token-guard]` 提醒 | ✅ |
| 守卫① 长任务不许前台 | **未启用**（阶段 B 前置未满足，交接文档 §0/§3） | 单元测试显式断言前台 `produce.py image/video` 放行 | ✅（按设计） |

测试：`tests/test_codex_token_guard.py` 18 项 + 原 `tests/test_token_guard.py` 18 项 = **36 项全过**。
守卫脚本 fail-open：任何内部异常退出 0 无输出，绝不阻塞生产。

## 2. 交接文档 §7 UNVERIFIED 项 — Codex 侧已全部实测定死

| 项 | 实测结论（探针 dump + 二进制内嵌 JSON Schema） |
|---|---|
| `tool_input.command` 字符串/数组 | **字符串**；shell 在 hook 边界 tool_name = `Bash`（三选正则正确且必要） |
| `view_image` 路径字段 | **`path`**，可能相对 `payload.cwd`（脚本已按 cwd 解析为绝对路径） |
| `Bash` 别名跨版本稳定性 | 0.171.0 实测 `Bash`；保留三选正则防漂移 |
| AGENTS.md 符号链接 | 未用软链，直接建真实文件 |
| `token_usage` 形状 | PostModelRequest 平铺：`input_tokens`（已含 cached）/`cached_input_tokens`/`output_tokens`/`total_tokens`，另有 `status`/`kind`/`request_id` |

**新发现（交接文档未覆盖，已按实测修正设计）**：
1. **PostModelRequest 的 `additionalContext` 被静默丢弃**——输出 schema 里有该字段，但真实调用中模型收不到、也无任何报错。因此守卫③做成两段式：PostModelRequest 只检测超阈值并写 pending 标记（`<tempdir>/drama-token-nudge-codex-pending-<session>.json`）；下一次 PreToolUse 以 `additionalContext` 注入（该注入点实测有效），一次性消费，每会话最多提醒一次。
2. PreToolUse 输出 `permissionDecision` 合法值 `allow|deny|ask`（二进制内嵌 schema 确认）→ Claude `deny()` 同形复用**成立**。
3. handler 字段实测可用：`command`/`timeout`/`statusMessage`（另有 `commandWindows`/`async`/`additionalContextLimit`）；matcher 组结构 `{matcher, hooks}`；PostModelRequest 配 `.*` 正常触发。
4. **boards 实际是 `.jpg`**——Claude 守卫 `find_boards` 只 glob `*.png`，对现有 atlas run 的 board-first 守卫实际不会触发（盲点）。Codex 版认 png/jpg/jpeg/webp。Claude 侧不在本次范围，未改，留待后续。

## 3. Hook 信任（已持久化，无需人工步骤）

2026-11-21 已通过官方 app-server RPC（`hooks/list` + `config/batchWrite`，与 TUI `/hooks` 同一写入路径）为本项目三个 handler 持久化信任，并在**不带任何绕过标志**的真实 exec 会话中验证拦截生效。

机制与坑（0.171.0 实测）：
- 信任存于 `~/.codex/config.toml` 的 `hooks.state."<key>".trusted_hash`；`<key>` 取自 `hooks/list` 返回的 `key`（形如 `<hooks.json 绝对路径>:<event>:<组>:<handler>`），**大小写敏感**（盘符大写原样）。
- `config/batchWrite` 参数：`edits:[{keyPath, value, mergeStrategy:"upsert"}]`；keyPath 引号段按 TOML 基本字符串解析，**Windows 反斜杠必须双写**，否则产生无效键。
- `--dangerously-bypass-hook-trust` 的 exec 会话会顺手写入**小写盘符**的信任键，与查询键不匹配 → 看似信任实则无效（本机已清理）。
- **哈希只覆盖 handler 配置（command/matcher/event/timeout 等），不含脚本内容**：实测改脚本内容哈希不变、信任保持。因此改 `codex_token_guard.py` 无需重新信任；改 `.codex/hooks.json` 的 handler 配置才需要（`/hooks` 或上述 RPC）。交接文档 §4.4「改脚本变哈希」与实测不符，以本节为准。

**探针开关**（CLI 升级后复核用，无需改配置、无需重新信任）：
- 开：在 `<tempdir>/drama-codex-hook-probe/` 建 `enabled.flag`，所有 hook payload 落盘该目录（保留最新 60 条）。
- 关：删除该目录。验证完务必关（dump 含本机路径）。
- 阈值覆盖：环境变量 `DRAMA_TOKEN_NUDGE_TOKENS`（默认 150000），不改脚本即可验证守卫③。

## 4. 基线与验收（不伪造节省数字）

- 改动前基线（2026-11-21，近 7 天，CC Switch 计费库）：**codex equiv 156.57M**（claude 734.19M / agy 139.27M 仅列作参照）。
- 本次 5 个最小验证会话合计 **88,258 equiv**（约为基线的 0.07%），其中第 5 次不带绕过标志、验证持久化信任。
- **节省尚未量化**。信任生效后跑一段可比工作，用 `python scripts/token_audit.py --app codex --days N` 按**每阶段 equiv** 对比；没有对照就不声称省了多少。

## 5. 阶段 B（未开工，别提前开守卫①）

前置：给 `produce.py image/video` 加「提交即返回」非阻塞入口（复用 `src/drama_studio/application/operations/tasks.py` 的异步任务运行器，返回 job id + 日志路径）。就位后再在 shell handler 启用守卫①（拒前台生成、指向新入口），并同步更新本文与测试。