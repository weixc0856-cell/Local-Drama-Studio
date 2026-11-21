# Token Economy 移植交接文档（Codex / Antigravity）

**读者**：接手实施的两个 AI 工具本身（OpenAI Codex CLI、Google Antigravity），以及转交本文的人。
**性质**：可执行交接说明。本文只做调研与规格，**未改动任何 Codex / Antigravity 配置**。
**调研日期**：2026-11-21。版本：Codex CLI `0.171.0`、Antigravity CLI `agy 1.5.13`。

> 路径一律用 `~` / `$CODEX_HOME` / `%LOCALAPPDATA%` 表示。仓库禁止写入盘符和用户名（见 CLAUDE.md 路径不变量）。

---

## 0. 先读这一条：不要照搬 Claude 的守卫

`scripts/hooks/token_guard.py` 的第一条守卫是这样判断的：

```python
if tool_input.get("run_in_background"):
    return False   # 后台跑，放行
```

**Codex 的 shell 工具没有 `run_in_background` 字段**（0.171.0 二进制里不存在该字符串；底层
`LocalShellExecAction` 只有 `command` / `timeout_ms` / `working_directory` / `env` / `user`）。
Antigravity 更没有脚本 hook。

直接移植的后果：该字段永远为假 → **每一次 `produce.py image/video` 都被拒 → 生产线直接瘫掉**，
不是省 token，是不能干活。所以必须按第 3 节的分期方案做，不要一次性全开。

---

## 1. 背景与实测基线

一次 15h 的 atlas 会话（Claude）实测 ≈ **12.3M 计费输入当量**：88.8M cache read + 2.66M
cache create + 180K output，约 500 次调用。根因是上下文 46K → 366K **全程零压缩**——中转模型
对外宣称 1M 窗口，auto-compact 永不触发。其中约 1.24M 是四次 >5min 空闲后的全量缓存重写。

**交付物全在磁盘上，上下文只是工作记忆。** 省钱的关键不是压缩本身，而是别让工作记忆一路长大。

规则原文见 CLAUDE.md「Token Economy & Session Hygiene」：一个阶段一个会话、长任务后台跑、
看板优先读图、Read/Grep 代替 shell peeking。

---

## 2. 三工具能力对照（已核实）

| 能力 | Claude Code | Codex CLI | Antigravity |
|---|---|---|---|
| 指令文件 | `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` / `GEMINI.md` |
| 自动压缩阈值可配 | 是（env） | **是**（config.toml） | **否**（后端强制） |
| 脚本 hook | PreToolUse | **有**，同形 | **无** |
| 静态命令拦截 | 权限设置 | 权限设置 | `deny`/`ask`/`allow` 规则 |
| 上下文用量可见 | transcript | `PostModelRequest` | `/context` 分类明细 |
| 计费入账 | 代理实时 | 会话日志摄取 | 会话日志摄取 |

**结论：一份共享 `AGENTS.md` 能同时喂 Codex 和 Antigravity；执行层必须各写各的。**

---

## 3. 分期方案（重要）

守卫分三条，可移植性差别很大：

| 守卫 | Claude 依赖 | Codex | Antigravity |
|---|---|---|---|
| ① 长任务不许前台跑 | `run_in_background` | **需重新设计** | 只能静态拦命令 |
| ② 有 boards 时不许读单图 | 拦 `Read` | 可做（`view_image`） | **做不到** |
| ③ 150K 阶段提醒 | transcript JSONL | 可做（`PostModelRequest`） | **做不到** |

### 阶段 A —— 立刻可做，零风险
共享 `AGENTS.md` + Codex 压缩阈值 + Codex 守卫②③ + Antigravity 规则文件。
这些都不会阻断生产。

### 阶段 B —— 有前置依赖，别提前开
守卫①。**前置条件：先给 `produce.py image/video` 加一条「提交即返回」的非阻塞入口。**

理由：现在的「后台跑」是 Claude 特有能力。要让任何 agent 都堵不住前台等待，正确做法是把非阻塞
做进 CLI 本身——提交任务后立刻返回 job id + 日志路径，agent 想等也没得等。

**不用自建**：`src/drama_studio/application/operations/tasks.py`（约 2370 行起）已有完整异步任务
运行器——任务存储、日志落盘、状态机、取消、进程树清理，目前只接了 Web 端。复用它接一个 CLI 入口即可。

在阶段 B 完成前：
- Codex：**不要**启用守卫①。
- Antigravity：把生成命令放进 **`ask`** 而不是 `deny`——留一道人工确认，但不至于彻底不能出图。

---

## 4. Codex 执行清单

### 4.1 压缩阈值（等价于我们的 180K 兜底）

`~/.codex/config.toml` 顶层加：

```toml
model_auto_compact_token_limit = 180000
```

相关可选键（均已确认存在）：`model_auto_compact_token_limit_scope`（`total` 默认 /
`body_after_prefix`）、`model_post_turn_compact_threshold_percent`（0–100，0 关闭轮末压缩）、
`model_context_window`、`compact_prompt`。手动命令 `/compact`。

> 该文件含明文 bearer token 与 API key。**不要打印、不要提交、不要写进任何日志。**
> 只增改上述键，不要重写整个文件。

### 4.2 指令文件

加载链：`$CODEX_HOME/AGENTS.md`（本机存在但 0 字节）→ 仓库根 → CWD，**root→leaf 拼接，后者覆盖前者**，
会话启动时全量加载。合并总量受 `project_doc_max_bytes` 限制，**默认 32768 字节，超出静默截断**。

本机 CLAUDE.md 约 9.2KB，加全局约 10.9KB，余量充足。

两种接法，二选一：
- 建 `AGENTS.md`（推荐，Antigravity 也读它）；
- 或设 `project_doc_fallback_filenames` 把 `CLAUDE.md` 加为回退名（仅在无 AGENTS.md 时生效）。

### 4.3 Hook

配置写 **`.codex/hooks.json`**（项目需 trusted，本仓库已是）或 config.toml 的 `[hooks]`。
`matcher` 是**对 tool_name 及其别名的正则**。

```json
{"hooks":{"PreToolUse":[{"matcher":"^(Bash|shell|unified_exec)$","hooks":[
  {"type":"command","command":"python scripts/hooks/token_guard.py","timeout":15}]}]}}
```

- shell 调用在 hook 边界上以 **`Bash`** 别名匹配；内部枚举是 `shell` / `unified_exec` / `execve`，
  且后端可被 `experimental_use_unified_exec_tool` 切换。**用上面那个三选正则，别只写 `Bash`。**
- 拒绝 JSON 与 Claude **完全同形**，现有 `deny()` 函数可直接复用：
  ```json
  {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"..."}}
  ```
  exit 2 + stderr 亦可。
- **没有 Read 工具**，Codex 通过 shell 读文件。但 **`view_image` 是独立工具**——守卫②挂这里。
- payload 含 `session_id` / `cwd` / `hook_event_name` / `model` / `permission_mode` / `turn_id` /
  `tool_name` / `tool_use_id` / `tool_input` / `transcript_path`（可能为 null）。
  **PreToolUse 里没有 token 计数**；`token_usage` 只在 **`PostModelRequest`** 上——守卫③挂那里。

### 4.4 信任流程（容易踩）

**未信任的 hook 是 fail-open：直接跳过，拒绝逻辑根本不执行**，只在启动时打印一条警告。
也就是说「装了但没生效」是静默的。

- 用 CLI 里的 **`/hooks`** 重新信任（Desktop：Settings > Hooks）。
- **改动 `token_guard.py` 会改变哈希，重新触发审核**——每次改脚本都要再信任一次。
- 仅 `command` 类型 handler 可用。

### 4.5 落地前先验证（必做）

以下两项文档未确认，**不要凭猜测写死**：
1. `tool_input.command` 在 hook 边界是字符串还是 argv 数组；
2. `view_image` 的 `tool_input` 里图片路径的字段名。

探测办法：先挂一个只把 stdin 原样 dump 到临时文件的 hook，跑一次真实 shell 调用和一次看图，
读那个文件确认字段，再写正式逻辑。**验证完删掉探测 hook。**

---

## 5. Antigravity 执行清单

### 5.1 配置位置（注意不在 `.antigravity`）

配置根是 **`~/.gemini/`**（与 Gemini CLI 共用）：app 状态 `~/.gemini/antigravity/`，
CLI 状态 `~/.gemini/antigravity-cli/`。应用本体在 `%LOCALAPPDATA%\antigravity`，
CLI `agy.exe` 在 `~/.gemini/bin/`。

### 5.2 规则文件

工作区（逐级向上到仓库根）：`AGENTS.md`、`GEMINI.md`、`.agents/AGENTS.md`、`.agents/rules/*.md`
（旧版 `.agent/rules/` 也读）。全局：`~/.gemini/AGENTS.md`、`~/.gemini/GEMINI.md`、
`~/.gemini/config/AGENTS.md|GEMINI.md`、`~/.gemini/config/rules/*.md`。**本机这些目前都不存在。**

- 平铺的 `AGENTS.md` / `GEMINI.md` **恒为 always-on，不要写 frontmatter**。
- 放进 `rules/` 目录的文件**必须**有 YAML frontmatter：
  ```yaml
  ---
  trigger: always_on        # 或 model_decision / glob / manual
  description: ...          # model_decision 必填
  globs: ...                # glob 必填
  ---
  ```
  **缺失或非法 → 静默丢弃**，不报错。

### 5.3 原生预算（这就是我们搁置的 C 项）

两条硬预算：单文件 **24KB**（`@[label](path)` 展开后计）、全局 + always_on 合计 **20,000 token**。
超预算时最大的文件被降级成「路径 + 描述」指针。

所以规则要写短。**别把 CLAUDE.md 全文塞进去**——写 token 规则 + 指向 CLAUDE.md 的指针即可。

另外 `~/.agents/skills/` 下有 **100 个 skill**，Antigravity 也会读。用 **`/context`** 能直接看到
Rules / Skills / Subagents / Workflows / Plugins / MCP tools / Checkpoint buffer 的分类占用——
这比我们从计费库反推便宜得多，**先用它量一次再决定砍哪些**。

### 5.4 上下文

自动把旧轮次压成 checkpoint summary；`/compact` 手动，`/clear`（别名 `/new`）开新会话。
**阈值不可配**，后端强制（社区 issue 提到 ~140–150K，**未核实**）。
结论：**我们那个 180K 兜底在 Antigravity 这边是多余的，不要去找对应开关。**

### 5.5 拦截（无脚本 hook）

只有权限规则：`command(...)` 放进 `deny` / `ask` / `allow`，优先级 **Deny > Ask > Allow**，
默认字面量前缀匹配，或 `command(regex:...)`。

- CLI：`~/.gemini/antigravity-cli/settings.json` 的 `permissions` 键（**该文件本机尚未创建**）。
- App：仅 UI（Settings > General > Global Permissions）。
- 现状：`permissionPreset = AUTO`、`autoExecutionPolicy = CASCADE_..._AUTO`，且已累积
  **333 条 globalPermissionGrants.allow**。在 AUTO 之下， deny/ask 规则是唯一的刹车。

阶段 A 建议（不阻断生产）：
```
ask: command(python src/produce.py image)
ask: command(python src/produce.py video)
```
阶段 B 完成后再考虑改 `deny`。

守卫②③在 Antigravity **无法实现**，只能写进规则靠自觉。不要假装能拦。

---

## 6. 计量（三个工具已经统一，无需新建）

**已核实**：CC Switch 除代理 Claude 流量外，还**摄取** Codex 与 Antigravity 的会话日志，
全部落在同一张 `proxy_request_logs` 表：

| app_type | data_source | 语义 |
|---|---|---|
| `claude` | `proxy` | 2 |
| `codex` | `codex_session` | 1 |
| `agy` | `agy_session` | 2 |

所以「Antigravity 不能改 base_url 所以测不了」是错的——**不走代理照样有账**。

### 6.1 已修复的计量 bug（本次改动，已完成）

`input_token_semantics` 决定 `input_tokens` 是否已含缓存部分：
- **2（Anthropic 式）**：input **不含** cached，直接用。
- **1（OpenAI 式）**：input **已含** cached，必须先减 `cache_read`，否则缓存段被计费两次。

原公式对 Codex 行虚高 **8.22 倍**（全量实测 1297.29M → 修正后 157.84M）。
`scripts/token_audit.py` 已修，新增 `--app` 过滤，`tests/test_token_guard.py` 有回归测试（18 项通过）。

> 注意：Codex 的 `cache_creation_tokens` 恒为 0（OpenAI 不单独计缓存写入），
> 所以我们那套「1.25x 缓存重写」的成本模型在 Codex 上不适用。
> 此前引用的 Claude 12.3M 基线是语义 2，**不受此 bug 影响，仍然有效**。

### 6.2 验收命令

```bash
python scripts/token_audit.py --app claude --days 7
python scripts/token_audit.py --app codex  --days 7
python scripts/token_audit.py --app agy    --days 7
```

**验收标准**：改动前后各跑一段可比的工作，比较**每阶段 equiv**，而不是总量。
没有对照数据就不要声称省了多少——这正是当前 initiative 缺的一环。

---

## 7. 未核实项汇总（实施前请自行确认）

| 项 | 状态 |
|---|---|
| Codex `tool_input.command` 是字符串还是数组 | UNVERIFIED，用 dump hook 探测 |
| Codex `view_image` 路径字段名 | UNVERIFIED，同上 |
| Codex `Bash` 别名跨版本稳定性 | UNVERIFIED，故用三选正则 |
| Codex AGENTS.md 是否跟随符号链接 | UNVERIFIED，别依赖软链 |
| Antigravity 压缩阈值具体数值 | UNVERIFIED（~140–150K 来自社区 issue） |
| Antigravity 摘要是否注入新会话 | UNVERIFIED |
| Antigravity 是否存在未公开的自定义端点 | UNVERIFIED，按「没有」规划 |

---

## 8. 给接手工具的执行边界

1. **只做阶段 A**，阶段 B 等 CLI 非阻塞入口就位再说。
2. 改 `~/.codex/config.toml` 时**只增改指定键**，不要重写文件，不要打印其中的密钥。
3. 每写一处配置，**用一次真实调用验证它确实生效**——Codex 未信任 hook 和 Antigravity 非法
   frontmatter 都是**静默失效**，不验证就等于没装。
4. 规则文件写短指针，不要复制 CLAUDE.md 全文。
5. 不要伪造节省数字。没有对照审计就如实说「未量化」。