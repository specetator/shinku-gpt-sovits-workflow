# Integration validation — 2026-10-30

## Verified upstream contracts

| Component | Inspected revision | Contract used |
| --- | --- | --- |
| DeepSeek Harness | `ce7073d51254c26cd63b22a60835b8f948deb447` | `@deepseek-ai/dsh-mcp-client`, stdio, `serverName`, `toolCallTimeoutMs`, `--patch` overlay |
| Tencent dsh-qqbot | `25bcaa72bab9ef0bd8f7ce8a2a9f9e4366f55639` (`0.5.4` in package.json) | `qqbot_send_file({file_path})`, automatic current-conversation target, WAV → `sendVoice`, `sendFile.extraRoots` |
| MCP Python SDK | `1.30.0` | FastMCP stdio discovery, structured + text tool results, visible tool errors |

Source references:

- [DSH MCP client reference](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/mcp/mcp-client/README.md)
- [DSH standalone overlay example](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/docs/user/guide/mcp-memory.md)
- [QQ send-file tool and target selection](https://github.com/tencent-connect/dsh-qqbot/blob/25bcaa72bab9ef0bd8f7ce8a2a9f9e4366f55639/src/media/send-file-tool.ts)
- [QQ extension dispatch and allowlist](https://github.com/tencent-connect/dsh-qqbot/blob/25bcaa72bab9ef0bd8f7ce8a2a9f9e4366f55639/src/media/send-media.ts)
- [QQ SDK sender wiring](https://github.com/tencent-connect/dsh-qqbot/blob/25bcaa72bab9ef0bd8f7ce8a2a9f9e4366f55639/src/gateway/bootstrap.ts)

## Completed checks

- **8 Python tests passed**, including a real HTTP test server and a separate MCP subprocess: JSON/Unicode payloads, language selection, emotion mapping, unique outputs, Hermes-compatible CLI flags, invalid inputs, HTTP failures, malformed/truncated WAV, OGG conversion failure, MCP discovery, QQ handoff arguments and MCP error propagation.
- **Real GPT-SoVITS model inference passed** using the existing Shinku v2Pro weights on a temporary loopback endpoint (`127.0.0.1:19880`): Japanese neutral WAV, 154,924 bytes / 2.42 s; Chinese neutral OGG, 22,730 bytes / 3.18 s. `ffprobe` identified the latter as Opus, 48 kHz, mono.
- **Real MCP → GPT-SoVITS inference passed** with the local `soft` emotion reference: 170,284-byte / 2.66-second WAV. MCP returned an existing absolute path, `delivery: pending`, and `qqbot_send_file` arguments.
- **Upstream QQ tool contract test passed** on Node 24.14.1: executed the actual `registerSendFileTool` and media-dispatch implementation against a mock sender. WAV reached `sendVoice` with the current conversation target; out-of-allowlist paths, missing conversation targets and simulated upload failures were rejected.
- **Overlay generation passed** with the project virtual environment and an explicit local configuration.

Reproduce the offline tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests/qq_voice_contract.mjs work/dsh-qqbot outputs/audio/your-generated.wav
```

The second command takes a checkout of the Tencent plugin as its first argument. It never contacts QQ. For a live model test (also no QQ send):

```powershell
.\.venv\Scripts\python.exe scripts/smoke_mcp.py --config configs/tts.local.json
```

## Remaining acceptance boundary

No authenticated QQ message was sent during this update. The native voice path is grounded in the upstream implementation and its executed dispatch test; delivery to an actual QQ client, playback there, and a model-driven DSH conversation still need acceptance in the user's connected QQ profile. The complete DSH host was not launched during these tests.

The extension does not modify existing Hermes/DSH profiles, QQ credentials, or active service ports. The temporary inference process was stopped after verification. Generated audio and local machine configurations remain outside version control.

DSH Web does not currently render MCP audio blocks as native voice bubbles. This integration returns paths/text and delegates QQ delivery to the QQ plugin. Run the MCP process and QQ plugin with access to the same filesystem. Speech files persist in `output_dir` until explicitly cleaned up.

Language detection is a convenience heuristic; explicit `lang` is required for ambiguous or unsupported automatic detection cases. The tests check protocol, container validity and routing, not a subjective voice-quality rating. Upstream developer-preview releases may change interfaces; the revision links above identify the inspected implementation.
