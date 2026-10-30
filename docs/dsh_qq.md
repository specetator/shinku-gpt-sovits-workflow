# DeepSeek Harness / QQ 原生语音接入

真红模型通过同一套 GPT-SoVITS `/tts` 服务供 Hermes 和 DSH 使用。DSH 侧复用腾讯的 [`@tencent-connect/dsh-qqbot`](https://github.com/tencent-connect/dsh-qqbot) 插件发送 QQ 原生语音：

```text
QQ 用户请求语音回复
  → DSH 调用 mcp__shinku__generate_qq_voice
  → GPT-SoVITS 生成真红 WAV，保存到 DSH 主机
  → DSH 调用 qqbot_send_file({file_path: 返回的绝对路径})
  → QQ 插件 sendVoice → 当前私聊/群聊的语音气泡
```

QQ 插件已有 WAV 扩展名分派、当前会话路由、路径白名单和媒体上传。本仓库提供合成端，直接复用这些接口，无需修改 QQ 插件源码。插件源码与验证记录见 [validation.md](validation.md)。

## 1. 配置合成端

先按仓库首页启动 GPT-SoVITS API，再在本仓库根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
Copy-Item configs/tts.example.json configs/tts.local.json
```

编辑 `configs/tts.local.json`：

- `api_url`：完整的 GPT-SoVITS `/tts` 地址，可指向另一台 GPU 主机。
- `reference.ref_audio_path`：**GPT-SoVITS 主机**能读取的参考音频路径；使用仓库中的 `model/reference_shinku_00003390.wav`。
- `reference.prompt_text` / `prompt_lang`：参考音频原文及语言。
- `output_dir`：**DSH / QQ 插件主机**上的输出目录。相对路径以配置文件所在目录为基准；默认落在仓库 `outputs/audio`。
- `timeout_seconds`：合成 HTTP 超时，默认 120 秒，最大 150 秒。

Linux 使用 `.venv/bin/python`，复制配置使用 `cp`。MCP 进程与 QQ 插件必须能读取同一份输出文件；远程 GPU 只需提供 HTTP API，不必共享参考音频目录。

先测试单次合成：

```powershell
.\.venv\Scripts\python.exe scripts/shinku_tts.py --text "今日はいい天気ですね。" --lang ja
```

命令返回 JSON，包含 `file_path`、格式、时长和语言。WAV 不需要客户端安装 FFmpeg。

## 2. 挂载 DSH MCP 工具

使用刚安装 MCP 依赖的 Python 生成独立 overlay：

```powershell
.\.venv\Scripts\python.exe scripts/configure_dsh.py
```

生成 `integrations/dsh/shinku.local.yml`，其中包含解释器、脚本和配置文件的绝对路径。文件使用 JSON 语法（有效 YAML），可以直接交给 DSH。此命令不修改已有 profile，且拒绝覆盖同名 overlay；迁移路径时可通过 `--output` 指定新文件。

为已有 QQ profile 启用合成工具：

```powershell
npx @deepseek-ai/dsh --profile qqbot --patch "$PWD/integrations/dsh/shinku.local.yml"
```

将 `qqbot` 替换为你已有的 profile 名称。纯 Web 使用：

```powershell
npx @deepseek-ai/dsh web --patch "$PWD/integrations/dsh/shinku.local.yml"
```

DSH 启动后应出现：

| 工具 | 用途 |
| --- | --- |
| `mcp__shinku__list_emotions` | 列出已配置情绪 |
| `mcp__shinku__synthesize` | 生成 WAV，返回本地文件路径 |
| `mcp__shinku__generate_qq_voice` | 生成 WAV，并返回 `qqbot_send_file` 的下一步参数 |

MCP 调用超时设置为 180 秒，覆盖合成端的 HTTP 超时。配置修改后重新启动 MCP 所在 profile。没有 QQ 插件时仍可用 `synthesize` 获取 WAV。

## 3. 复用腾讯 QQ 插件

已有 QQ 插件的 profile 直接使用；首次安装按 [腾讯插件安装说明](https://github.com/tencent-connect/dsh-qqbot#安装) 完成扫码绑定。例如：

```powershell
npx @deepseek-ai/dsh plugin --profile qqbot add @tencent-connect/dsh-qqbot
```

在现有 QQ 插件配置中，将本项目输出目录加入 `sendFile.extraRoots`，保留原有白名单和其他配置。例如：

```yaml
sendFile:
  restrictPaths: true
  extraRoots:
    - 'F:/AI_audio/shinku-gpt-sovits-workflow/outputs/audio'
```

这是 **QQ 插件 config 内部的字段**，不是独立 DSH overlay。生成脚本会打印本机实际应加入的目录。若输出目录已经位于 QQ 插件配置的 `cwd` 下，则无需另加白名单。

在 QQ 会话中发出：

> 用真红的声音回复“今日はいい天気ですね。”，生成后通过 QQ 语音发给我。

预期工具顺序：

```text
mcp__shinku__generate_qq_voice({"text":"今日はいい天気ですね。","lang":"ja"})
qqbot_send_file({"file_path":"第一步实际返回的绝对路径"})
```

`generate_qq_voice` 返回 `delivery: "pending"` 和 `qq_arguments`，表示音频已生成、等待发送。`qqbot_send_file` 省略 `target`，由 QQ 插件绑定当前会话。发送失败时查看 QQ 工具错误，不要再次生成同一段音频。

如希望 Agent 稳定选择这条链路，可将以下内容**追加**到现有 QQ 插件 `directPrompt` / `groupPrompt` 或所用 preset 的指令中：

> 用户请求语音回复时，先调用 mcp__shinku__generate_qq_voice，随后将返回的 qq_arguments 原样传给 qqbot_send_file，不填写 target。只有 QQ 发送工具成功后才确认已发送。不要把同一音频再作为附件重复发送。非 neutral 情绪先通过 list_emotions 查询。

## 4. 情绪参考音频

在配置中新增 `emotion_refs`，指向已有 `emotion_refs.json`。相对路径以配置文件目录为基准，文件内的 `ref_audio_path` 仍属于 GPT-SoVITS 主机：

```json
{
  "soft": {
    "ref_audio_path": "F:/AI_audio/shinku_emotion_refs/soft.wav",
    "prompt_text": "それなら その干渉 私の力で直そうか",
    "prompt_lang": "ja"
  }
}
```

支持已有七种标签的映射文件：`neutral / happy / soft / sad / angry / surprised / excited`；实际可选项以文件内容为准。未知情绪会明确报错。未配置情绪文件时使用 `reference` 提供的 neutral 声音。

语言自动检测优先识别日文假名，其次汉字，其余按英文；纯汉字日语和其他语言请显式指定 `lang`。模型原始训练语言为日语，中文等效果以试听为准。

## Hermes 与普通脚本

Hermes 的外部 TTS 命令可复用同一个 CLI，参数沿用 `--text-file` / `--output` / `--lang` / `--format`：

```powershell
python scripts/shinku_tts.py --config configs/tts.local.json --text-file reply.txt --output outputs/reply.ogg --format ogg
```

OGG 使用 FFmpeg 转为 Opus，适用于 Telegram 原生语音；QQ 使用默认 WAV，交给腾讯插件处理语音上传。需要 OGG 时安装带 `libopus` 的 FFmpeg，或通过配置字段 `ffmpeg` 指定可执行文件。转换失败会报错，不会把 WAV 数据伪装成 OGG。CLI 默认格式为 WAV；原 Hermes 包装器默认 OGG 的调用迁移时请显式加 `--format ogg`。

本扩展提供命令行接口，不改写用户现有 Hermes 配置。自动合成的文件使用唯一名称，存放在项目输出目录；根据需要定期归档或清理。

## 排查

| 现象 | 检查 |
| --- | --- |
| DSH 无真红工具 | overlay 中的 Python 是否安装 `requirements-mcp.txt`，本地 JSON 是否存在，查看 MCP stderr |
| 合成超时 / HTTP 错误 | API 是否启动，`api_url`、GPU 状态和服务端参考音频路径 |
| QQ 提示路径不允许 | `output_dir` 是否在 QQ `cwd` 或 `sendFile.extraRoots` 内 |
| QQ 无法确定发送目标 | 必须从 QQ 插件创建的私聊/群聊会话调用；普通 Web 会话没有 QQ 回复目标 |
| 生成成功但没有气泡 | 是否继续调用了 `qqbot_send_file`，该工具是否返回发送成功 |
| Web 界面仅显示路径 | DSH MCP bridge 目前不原生渲染 audio block；QQ 语音走独立的 `sendVoice` 路径 |

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests/qq_voice_contract.mjs work/dsh-qqbot outputs/audio/实际生成的文件.wav
```

第二条需要 Node 22.18+ 和腾讯 QQ 插件源码 checkout；它执行上游工具的真实路由代码，使用模拟发送器，不连接 QQ。当前验证范围和上游版本见 [validation.md](validation.md)。

另可执行 `python scripts/smoke_mcp.py --config configs/tts.local.json`，通过真实 MCP 子进程完成一次模型合成并打印 QQ 交接参数。
