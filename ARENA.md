# 🧠 ARENA.md —— Arena Agent 的第二大脑与手脚操作手册

> **仓库定位**：本仓库归 @zyou9724-creator 所有，同时是 **Arena.ai Agent 的常驻基地**。
> Arena 在任意新会话中可以：从这里**取工具**（可执行的视频/TTS/合成管线）、
> **取知识**（54+ 技能定义、29 个 Agent 分工、架构文档）、**沉淀成果**（脚本、笔记、产物索引）。
> —— 即"第二大脑"（跨会话记忆与知识）与"手脚"（真实执行能力）。
>
> 本文件写给**未来的 Arena 会话**：读完它，30 秒接管本仓库。

---

## 0. 新会话自举协议（30 秒）

```bash
git clone https://github.com/zyou9724-creator/bony-agent.git && cd bony-agent
bash scripts/arena/setup_arena.sh     # venv + 依赖 + ffmpeg/ffprobe 垫片自举
bash scripts/arena/e2e_test.sh        # 自检：能出一条短视频 = 环境完好
```

**沙箱生存须知（血泪教训）**：
- 持久化只信 **GitHub 远端**，工作区快照可能丢 `.git` / venv / `node_modules` / `.next`（都是常态，重装即可）。
- 推送令牌**不写进任何文件**，用 `git push "https://x-access-token:<令牌>@github.com/..."` 单次传入。
- 沙箱无 Go / Rust / Docker / 系统 ffmpeg / swap，内存 ≈2GB：后端与流水线够用，前端生产构建走 CI。
- `main.py` 导入时会把 ffmpeg/ffprobe 垫片自举到 `storage/bin`（本仓库自带能力）。

## 1. 能力索引（三档，全部实测）

### ✅ 免 Key 立即可用
| 能力 | 入口 |
| --- | --- |
| 一键短视频（主题→文案→配音→画面→字幕→1080×1920 MP4，约 34s） | `POST /tools/video/auto`，或 `bash scripts/arena/e2e_test.sh` |
| 免费真人配音 edge-tts（中日英多音色） | `tools/audio_tools.py: generate_speech_edge_tts()` |
| 29 专业 Agent 的 API（结构真实，文案走 LLM 桩） | `uvicorn main:app` 后 361 个端点 |
| 前端开发模式（1.3GB 峰值） | `cd web && npm install && npx next dev`（需 `web/.npmrc`，仓库已含） |
| OpenAI 兼容 LLM 桩（任何项目的干跑测试件） | `scripts/arena/llm_stub.py` + `LLM_PROVIDER=ollama` |

### 🔑 给 Key 即解锁
| Key | 解锁 |
| --- | --- |
| `PEXELS_API_KEY`（免费，首选） | 真实免版权 B-roll，成片质感飞跃 |
| `ALIBABA_API_KEY` / `ZHIPUAI_API_KEY` / `DEEPSEEK_API_KEY`… | 真实文案、全部 Agent 实战化 |
| `JIMENG_*` / `ARK_API_KEY` / `GOOGLE_API_KEY` | 生图、图生视频、短剧/播客流水线 |
| 配置后写 `backend/.env`（已 gitignore，**密钥永不入库**） | 模板见 `backend/.env.arena.example` |

### 🚫 沙箱物理禁止（需宿主机/CI）
Playwright 浏览器自动发布（14 平台）、Computer Use、Electron 打包、Go/Rust 引擎、`next build`（走 `.github/workflows/web-build.yml`）。

## 2. 可复用资产地图（"借鉴创作"用）

| 资产 | 位置 | 可复用点 |
| --- | --- | --- |
| 短视频流水线 | `backend/services/auto_video_pipeline.py` | 任务状态机 + 降级设计的范本 |
| TTS/混音/字幕 | `backend/tools/{audio,subtitle,material,media_common}_tools.py` | 可单独 import 到任何项目 |
| 29 Agent 分工定义 | `backend/agents/` | 多 Agent 编排的提示词/职责灵感库 |
| 54+ 技能卡 | `.agent/skills/` | 数字员工能力描述，可当 Agent 行为指南 |
| ffprobe 垫片 | `backend/tools/ffprobe_shim.py` | 任何缺 ffprobe 的容器即插即用 |
| 无 Key 干跑套件 | `scripts/arena/` | CI/沙箱自测范式：桩+降级+自检 |
| 更多环境细节 | `docs/ARENA_AI_AGENT.md` | 环境矩阵、实测数据 |

## 3. 工作约定（Arena 自律清单）

1. **大改走分支 + PR**（留评审痕迹），**小修补直推 main**（仓库所有者已授权自由编辑）。
2. 优先考虑反哺上游 `phuhao00/bony-agent`：通用修复（如 ffprobe 垫片）开上游 PR。
3. 生成产物一律落 `storage/`（已忽略），不落仓库。
4. 每次会话收尾：把可复用的脚本/笔记沉淀回本仓库（这就是"第二大脑"的记性）。
5. 涉及第三方平台自动化（发布链路等）前，先向仓库所有者确认范围与账号风险。

---
*建立：2026-07-19 会话 · 同步上游 66fdcd8 · 沙箱实测全链路 34s 出片 ✓*
