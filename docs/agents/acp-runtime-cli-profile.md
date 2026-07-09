# ACP Runtime CLI Profile 约定

## Profile 字段

| 字段 | 说明 |
|------|------|
| `runner` | 运行器标识（如 `codex_cli`） |
| `command` | argv 列表；支持占位符，**不经 shell** |
| `workspace_root` | 默认 workspace；节点 `workspace_root` 非空时优先 |
| `timeout_seconds` | CLI 超时秒数 |
| `environment` | 额外环境变量（会与进程 env 合并） |

## command 占位符

Runtime 在调用前将 `rendered_context` 写入 `session_dir/input/prompt.txt`，并对 command 每一项做字面量替换：

| 占位符 | 含义 |
|--------|------|
| `{context_file}` | `prompt.txt` 绝对路径（推荐） |
| `{context}` | 渲染后的全文（作为单一 argv） |
| `{session_dir}` | session 目录绝对路径 |
| `{skill_directory}` | Skill 目录绝对路径 |

**无占位符时不会自动追加参数**，以免破坏自定义 `python3 -c ...` 等命令。此时仍可通过文件与 env 读取上下文。

## 环境变量（默认注入）

| 变量 | 含义 |
|------|------|
| `RYAN_ACP_CONTEXT_FILE` | 同 `{context_file}` |
| `RYAN_ACP_SESSION_DIR` | 同 `{session_dir}` |

若 profile.`environment` 已设置同名键，则不覆盖。

## workspace_root 优先级

1. 节点 widget 非空字符串  
2. 否则 profile.`workspace_root`  
3. 否则 `output/acp_workspace`

## 示例

```json
{
  "runner": "codex_cli",
  "command": ["codex", "exec", "{context}"],
  "workspace_root": "output/acp_workspace",
  "timeout_seconds": 300,
  "environment": {}
}
```

真实 Claude/Codex 参数以联调为准；占位符机制固定。失败语义见固定 Agent 契约文档。
