#!/usr/bin/env python3
"""
scripts/assemble.py
쇼츠 최종 영상 합성 — 로컬 실행 전용 (Vercel 서버리스가 아님)

이유: FFmpeg 바이너리 + 실제 미디어 파일 처리가 필요해서
      서버리스 함수의 실행시간/파일시스템 제약에 맞지 않음.
      내 컴퓨터에서 실행합니다.

사전 준비물 (필수):
  1. FFmpeg 설치
     - Mac:     brew install ffmpeg
     - Windows: https://www.gyan.dev/ffmpeg/builds/ (경로에 PATH 추가)
     - Linux:   sudo apt install ffmpeg

  2. 프로젝트 폴더 구성:
     my_episode/
       script.json      ← 앱에서 "📄 script.json 내보내기" 버튼으로 다운로드
       scene_01.jpg     ← Pexels/AI에서 다운로드한 이미지 (jpg/png/webp)
       scene_01.mp3     ← 앱 "🔊 음성" 탭에서 다운로드한 오디오
       scene_02.jpg
       scene_02.mp3
       ... (장면 수만큼)

  이미지나 오디오가 없는 장면은 자동으로 대체됩니다:
    - 이미지 없음 → 카테고리 색상의 단색 배경
    - 오디오 없음 → 무음 (기본 5초)

실행 방법:
  python scripts/assemble.py --project ./my_episode
  python scripts/assemble.py --project ./my_episode --bgm ./music.mp3 --bgm-volume 0.12

출력:
  my_episode/DOWNLOAD_READY/final.mp4
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

# ── 설정 ──────────────────────────────────────

WIDTH, HEIGHT, FPS = 1080, 1920, 25
DEFAULT_SCENE_DURATION = 5.0   # 오디오 없을 때 기본 장면 길이(초)
AUDIO_PAD = 0.3                # 오디오 끝에 여유 시간(초)
IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".webp"]

# 카테고리별 배경색 (이미지 없을 때 플레이스홀더) — 앱 UI 색상과 통일
CATEGORY_COLORS = {
    "kpop":     "FF2D55",
    "social":   "FFD60A",
    "culture":  "30D158",
    "overseas": "0A84FF",
    "beauty":   "BF5AF2",
    "living":   "FF9F0A",
    "season":   "32ADE6",
}
DEFAULT_COLOR = "6E6E82"

# 한글 자막용 폰트 후보 경로 (OS별) — 순서대로 탐색해서 첫 번째로 존재하는 것 사용
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",   # Linux (Noto)
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",           # Linux (Nanum)
    "C:/Windows/Fonts/malgun.ttf",                               # Windows (맑은 고딕)
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",                # macOS
    "/Library/Fonts/AppleGothic.ttf",                            # macOS 구버전
]


# ── 유틸 ──────────────────────────────────────

def find_font(override: str | None) -> str | None:
    """자막용 한글 폰트 경로 탐색. 못 찾으면 None (자막 없이 진행)."""
    if override and Path(override).exists():
        return override
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def check_ffmpeg():
    """ffmpeg/ffprobe 설치 여부 확인. 없으면 안내 후 종료."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("❌ FFmpeg가 설치되어 있지 않습니다.")
        print("   Mac:     brew install ffmpeg")
        print("   Windows: https://www.gyan.dev/ffmpeg/builds/")
        print("   Linux:   sudo apt install ffmpeg")
        sys.exit(1)


def get_audio_duration(path: Path) -> float:
    """ffprobe로 오디오 길이(초) 측정."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"  ⚠️  오디오 길이 측정 실패 ({path.name}): {e}")
        return DEFAULT_SCENE_DURATION


def find_scene_file(folder: Path, prefix: str, exts: list[str]) -> Path | None:
    """scene_01.jpg / scene_01.png 등 확장자 여러 개 중 존재하는 파일 탐색."""
    for ext in exts:
        candidate = folder / f"{prefix}{ext}"
        if candidate.exists():
            return candidate
    return None


def wrap_subtitle(text: str, max_chars: int = 16, max_lines: int = 2) -> str:
    """자막이 너무 길면 줄바꿈 (세로 영상 폭에 맞춤)."""
    if not text:
        return ""
    lines = textwrap.wrap(text, width=max_chars)
    return "\n".join(lines[:max_lines])


# ── 장면별 클립 생성 ────────────────────────────

def build_scene_clip(
    scene: dict,
    image_path: Path | None,
    audio_path: Path | None,
    category_color: str,
    font_path: str | None,
    tmp_dir: Path,
    out_path: Path,
):
    """
    장면 하나를 완결된 mp4 클립으로 렌더링.
    - 이미지 있음: 쾄번즈(천천히 확대) 효과
    - 이미지 없음: 카테고리 색상 단색 배경
    - 오디오 있음: 그 길이에 맞춤 / 없음: 기본 길이 + 무음
    - 자막: scene['subtitle'] 있으면 하단에 박스와 함께 번인
    """
    has_audio = audio_path is not None
    duration = get_audio_duration(audio_path) + AUDIO_PAD if has_audio else DEFAULT_SCENE_DURATION
    n_frames = max(1, int(duration * FPS))

    # ── 자막 텍스트 파일 준비 (drawtext textfile 방식 — 한글/특수문자 이스케이프 문제 회피) ──
    subtitle_filter = ""
    subtitle_text = wrap_subtitle(scene.get("subtitle", ""))
    if subtitle_text and font_path:
        sub_file = tmp_dir / f"sub_{scene['num']}.txt"
        sub_file.write_text(subtitle_text, encoding="utf-8")
        # 경로에 콜론/특수문자 있을 수 있어 이스케이프
        safe_path = str(sub_file).replace("\\", "/").replace(":", "\\:")
        safe_font = font_path.replace("\\", "/").replace(":", "\\:")
        subtitle_filter = (
            f",drawtext=fontfile='{safe_font}':textfile='{safe_path}':"
            f"fontsize=64:fontcolor=white:line_spacing=12:"
            f"box=1:boxcolor=black@0.55:boxborderw=28:"
            f"x=(w-text_w)/2:y=h-360"
        )
    elif subtitle_text and not font_path:
        print(f"  ⚠️  장면 {scene['num']}: 한글 폰트를 못 찾아 자막 없이 진행합니다.")

    # ── 비디오 입력 소스 구성 ──
    if image_path:
        video_input = ["-loop", "1", "-i", str(image_path)]
        # 커버 채우기 + 크롭 + 쾄번즈(서서히 확대)
        video_filter = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"zoompan=z='min(zoom+0.0015,1.15)':d={n_frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"
            f"{subtitle_filter}"
        )
    else:
        video_input = ["-f", "lavfi", "-i",
                        f"color=c=0x{category_color}:s={WIDTH}x{HEIGHT}:d={duration}:rate={FPS}"]
        video_filter = f"format=yuv420p{subtitle_filter}" if subtitle_filter else "null"

    # ── 오디오 입력 소스 구성 ──
    if has_audio:
        audio_input = ["-i", str(audio_path)]
    else:
        audio_input = ["-f", "lavfi", "-i",
                        f"anullsrc=channel_layout=mono:sample_rate=44100"]

    cmd = [
        "ffmpeg", "-y",
        *video_input,
        *audio_input,
        "-filter_complex", f"[0:v]{video_filter}[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-t", f"{duration:.2f}",
        "-r", str(FPS),
        str(out_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ 장면 {scene['num']} 렌더링 실패:")
        print(result.stderr[-800:])
        return False
    return True


# ── 전체 합성 ────────────────────────────────

def assemble(project_dir: Path, bgm_path: Path | None, bgm_volume: float, font_override: str | None):
    check_ffmpeg()

    script_path = project_dir / "script.json"
    if not script_path.exists():
        print(f"❌ script.json이 없습니다: {script_path}")
        print("   앱의 '📄 script.json 내보내기' 버튼으로 먼저 다운로드하세요.")
        sys.exit(1)

    data = json.loads(script_path.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    category = data.get("type", "")
    color = CATEGORY_COLORS.get(category, DEFAULT_COLOR)

    if not scenes:
        print("❌ script.json에 장면이 없습니다.")
        sys.exit(1)

    font_path = find_font(font_override)
    if not font_path:
        print("⚠️  한글 폰트를 찾지 못했습니다. 자막 없이 진행합니다.")
        print("   --font 옵션으로 폰트 경로(.ttf/.ttc)를 직접 지정할 수 있습니다.")

    print("=" * 55)
    print(f"  영상 합성 시작: {data.get('topic', '(제목 없음)')}")
    print(f"  장면 수: {len(scenes)}개 | 카테고리: {category or '미지정'}")
    print("=" * 55)

    ready_dir = project_dir / "DOWNLOAD_READY"
    ready_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        clip_paths = []

        for scene in scenes:
            num = scene["num"]
            prefix = f"scene_{num:02d}"
            image_path = find_scene_file(project_dir, prefix, IMAGE_EXTS)
            audio_path = project_dir / f"{prefix}.mp3"
            audio_path = audio_path if audio_path.exists() else None

            if not image_path:
                print(f"  ⚠️  장면 {num}: 이미지 없음 → 색상 배경으로 대체")
            if not audio_path:
                print(f"  ⚠️  장면 {num}: 오디오 없음 → 무음 {DEFAULT_SCENE_DURATION}초로 대체")

            clip_out = tmp_dir / f"clip_{num:02d}.mp4"
            print(f"  [{num}/{len(scenes)}] 렌더링 중...")
            ok = build_scene_clip(scene, image_path, audio_path, color, font_path, tmp_dir, clip_out)
            if ok:
                clip_paths.append(clip_out)

        if not clip_paths:
            print("❌ 렌더링된 장면이 하나도 없습니다. 중단합니다.")
            sys.exit(1)

        # ── concat demuxer로 전체 이어붙이기 ──
        concat_list = tmp_dir / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in clip_paths), encoding="utf-8"
        )

        slideshow_path = tmp_dir / "slideshow.mp4"
        print("\n  전체 장면 이어붙이는 중...")
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
             "-c", "copy", str(slideshow_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("❌ 이어붙이기 실패:")
            print(result.stderr[-800:])
            sys.exit(1)

        final_path = ready_dir / "final.mp4"

        # ── 배경음악 믹스 (선택) ──
        if bgm_path and bgm_path.exists():
            print(f"  배경음악 믹스 중 ({bgm_path.name}, 볼륨 {bgm_volume})...")
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", str(slideshow_path), "-stream_loop", "-1", "-i", str(bgm_path),
                 "-filter_complex",
                 f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]",
                 "-map", "0:v", "-map", "[a]",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                 "-shortest", str(final_path)],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                print("  ⚠️  배경음악 믹스 실패, 배경음악 없이 저장합니다:")
                print(result.stderr[-500:])
                shutil.copy(slideshow_path, final_path)
        else:
            shutil.copy(slideshow_path, final_path)

    print("\n" + "=" * 55)
    print(f"✅ 완료: {final_path.resolve()}")
    print("=" * 55)


# ── CLI ──────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="쇼츠 영상 합성 (로컬 실행)")
    parser.add_argument("--project", required=True, help="프로젝트 폴더 경로 (script.json + 이미지/오디오)")
    parser.add_argument("--bgm", default=None, help="배경음악 파일 경로 (선택)")
    parser.add_argument("--bgm-volume", type=float, default=0.15, help="배경음악 볼륨 (기본 0.15)")
    parser.add_argument("--font", default=None, help="자막용 폰트 파일 경로 직접 지정 (선택)")
    args = parser.parse_args()

    project_dir = Path(args.project).expanduser().resolve()
    if not project_dir.exists():
        print(f"❌ 프로젝트 폴더가 없습니다: {project_dir}")
        sys.exit(1)

    bgm_path = Path(args.bgm).expanduser().resolve() if args.bgm else None
    assemble(project_dir, bgm_path, args.bgm_volume, args.font)


if __name__ == "__main__":
    main()
