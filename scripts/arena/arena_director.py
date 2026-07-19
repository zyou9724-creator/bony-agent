#!/usr/bin/env python3
"""arena_director.py —— Arena 导演模式（第一档·无 Key 能力的全强化版）。

核心思想：Arena Agent 本身就是 LLM / 生图引擎 / 配音员，短视频流水线里
三个"桩/降级"环节全部由 Agent 亲自供电：

  旁白文案   --script/--script-file   Agent 亲自撰写（可结合 web 检索）
  B-roll 素材 --images a.jpg b.jpg    Agent 生成/检索的图片 → FFmpeg Ken Burns
                                       推拉摇移动态片段（替换 synthetic 色块）
  配音       --audio voice.mp3        Agent 生成的语音直用（替换 edge-tts）

凡未显式提供的环节，自动回落到流水线默认行为（LLM 桩 / synthetic / edge-tts）。
不改动 backend 任何源码：仅在本进程内对 services.auto_video_pipeline 做
函数替换（monkeypatch），对桌面/服务器部署零影响。

用法示例（repo 根目录）：
  arena-venv/bin/python scripts/arena/arena_director.py \
      --subject "东京周边一日避暑指南" \
      --script-file /tmp/script.txt \
      --terms "高尾山,江之岛,秩父" \
      --images /tmp/1.jpg /tmp/2.jpg /tmp/3.jpg \
      --audio /tmp/voice.mp3 \
      --workdir /tmp/arena_run
退出码：0=完成，1=失败。结果 JSON 打印到 stdout 末尾。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, "backend")
FFMPEG = None  # resolve lazily from storage/bin (main.py 自举)


def _sh(cmd: list) -> bool:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def _ken_burns_clip(img: str, out: str, seconds: float, w: int = 1080, h: int = 1920, fps: int = 24) -> bool:
    """单张图片 → 缓慢推近的动态竖屏片段；失败则回落静态画面。"""
    frames = max(int(seconds * fps), fps)
    vf = (
        f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
        f"crop={w*2}:{h*2},"
        f"zoompan=z='min(zoom+0.0012,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={w}x{h}:fps={fps},format=yuv420p"
    )
    ok = _sh([FFMPEG, "-y", "-loop", "1", "-i", img, "-vf", vf,
              "-t", f"{seconds:.2f}", "-c:v", "libx264", "-preset", "veryfast", out])
    if not ok or not os.path.isfile(out):
        # 静态兜底：缩放填充 + 固定时长
        vf2 = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
               f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p")
        ok = _sh([FFMPEG, "-y", "-loop", "1", "-i", img, "-vf", vf2,
                  "-t", f"{seconds:.2f}", "-c:v", "libx264", "-preset", "veryfast", out])
    return ok and os.path.isfile(out)


def build_image_materials(images: list, task_dir: str, target_duration: float, clip_duration: float) -> list:
    """按目标时长循环图片，生成 Ken Burns 片段列表（契约与 material_tools 一致）。"""
    os.makedirs(task_dir, exist_ok=True)
    clips, total, i = [], 0.0, 0
    while total < target_duration and i < len(images) * 4:
        src = images[i % len(images)]
        i += 1
        out = os.path.join(task_dir, f"arena_m_{i:03d}.mp4")
        if _ken_burns_clip(src, out, clip_duration):
            clips.append(out)
            total += clip_duration
    return clips


def main() -> int:
    ap = argparse.ArgumentParser(description="Arena 导演模式 —— Agent 亲自供电的一键短视频")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--script", default="", help="旁白文案文本")
    ap.add_argument("--script-file", default="", help="旁白文案文件（UTF-8）")
    ap.add_argument("--terms", default="", help="素材检索词，逗号分隔")
    ap.add_argument("--images", nargs="*", default=[], help="Agent 准备好的 B-roll 图片")
    ap.add_argument("--audio", default="", help="Agent 准备好的配音文件(mp3/wav)")
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural", help="--audio 缺省时的 edge-tts 音色")
    ap.add_argument("--bgm", default="none")
    ap.add_argument("--clip-duration", type=float, default=3.0)
    ap.add_argument("--no-subtitle", action="store_true")
    args = ap.parse_args()

    script = args.script
    if not script and args.script_file:
        with open(args.script_file, encoding="utf-8") as f:
            script = f.read().strip()
    terms = [t.strip() for t in args.terms.split(",") if t.strip()]
    images = [os.path.abspath(p) for p in args.images if os.path.isfile(p)]
    audio = os.path.abspath(args.audio) if args.audio and os.path.isfile(args.audio) else ""

    # ── 进入后端环境：import main 会自举 ffmpeg/ffprobe 垫片到 storage/bin ──
    os.chdir(BACKEND)
    sys.path.insert(0, BACKEND)
    os.environ.setdefault("LLM_PROVIDER", os.environ.get("LLM_PROVIDER", "ollama"))
    import main as _main  # noqa: F401  (副作用：_setup_ffmpeg + 依赖就绪)

    global FFMPEG
    FFMPEG = os.path.join(ROOT, "storage", "bin", "ffmpeg")

    from services import auto_video_pipeline as pl

    # ── 供电点 1：Agent 图片素材接管（替换下载/synthetic）──
    if images:
        def _arena_download(search_terms, target_duration, task_dir, source, aspect_ratio, clip_duration, **kw):
            paths = build_image_materials(images, os.path.join(task_dir, "arena"), target_duration, clip_duration)
            if not paths:
                raise RuntimeError("Agent 图片素材生成失败")
            return paths, "arena-images"
        pl.download_materials_for_duration = _arena_download
        print(f"[director] B-roll: {len(images)} 张 Agent 图片（Ken Burns 动态化）", flush=True)

    # ── 供电点 2：Agent 配音接管（替换 edge-tts）──
    if audio:
        def _arena_tts(text, voice=None, output_name=""):
            return {"success": True, "local_path": audio, "engine": "arena-voice"}
        pl.generate_speech_edge_tts = _arena_tts
        print(f"[director] 配音: Agent 语音 {os.path.basename(audio)}", flush=True)

    print(f"[director] 旁白: {'Agent 亲撰' if script else '回落流水线默认'}", flush=True)

    params = pl.AutoVideoParams(
        subject=args.subject,
        script=script,
        search_terms=terms,
        voice=args.voice,
        bgm=args.bgm,
        clip_duration=args.clip_duration,
        subtitle_enabled=not args.no_subtitle,
    )
    task_id = pl.create_auto_video_task(params)
    print(f"[director] task_id={task_id} 开拍……", flush=True)
    pl.run_auto_video_task(task_id, params)  # 同步执行，进度经 task_manager 记录

    task = pl.get_auto_video_task(task_id) or {}
    status = task.get("status")
    result = task.get("result") or {}
    print("[director]", "✅ 杀青" if status == "completed" else f"❌ 失败: {task.get('error')}", flush=True)
    print(json.dumps({
        "status": status,
        "video_path": result.get("video_path"),
        "duration_sec": result.get("duration_sec"),
        "material_mode": result.get("material_mode"),
        "message": task.get("message"),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
