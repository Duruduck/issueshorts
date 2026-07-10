# 🎬 영상 합성 가이드 (assemble.py)

앱에서 만든 대본 + 이미지 + 음성을 최종 쇼츠 mp4로 합칝니다.
**로컬 컴퓨터에서 실행**합니다 (Vercel 서버리스가 아님 — FFmpeg와 실제 미디어 파일 처리가 필요해서).

---

## 1. 사전 준비 (최초 1회)

### FFmpeg 설치
```bash
# Mac
brew install ffmpeg

# Windows
# https://www.gyan.dev/ffmpeg/builds/ 에서 다운로드 후 PATH 등록

# Linux
sudo apt install ffmpeg
```

### 한글 자막 폰트 (자동 탐색, 보통 별도 설치 불필요)
Windows는 `맑은 고딕`, Mac은 `Apple SD Gothic Neo`가 기본 내장되어 자동으로 잡힐니다.
못 찾으면 자막 없이 진행되고, `--font` 옵션으로 직접 지정 가능합니다.

---

## 2. 프로젝트 폴더 만들기

```
my_episode/
├── script.json      ← 앱 "📝 대본" 탭 → "📄 script.json 내보내기" 버튼
├── scene_01.jpg      ← 앱 "🎨 이미지" 탭에서 다운로드 (jpg/png/webp 아무거나)
├── scene_01.mp3      ← 앱 "🔊 음성" 탭에서 다운로드
├── scene_02.jpg
├── scene_02.mp3
└── ... (장면 수만큼)
```

**이미지나 음성이 없는 장면이 있어도 괜찮습니다:**
- 이미지 없음 → 카테고리 색상 배경으로 자동 대체
- 음성 없음 → 무음 5초로 자동 대체

파일명은 반드시 `scene_01`, `scene_02`... 형식(2자리 숫자)을 지켜야 합니다.

---

## 3. 실행

```bash
python scripts/assemble.py --project ./my_episode
```

배경음악을 넣고 싶으면:
```bash
python scripts/assemble.py --project ./my_episode --bgm ./music.mp3 --bgm-volume 0.15
```

폰트를 직접 지정하고 싶으면:
```bash
python scripts/assemble.py --project ./my_episode --font "/path/to/font.ttf"
```

---

## 4. 결과물

```
my_episode/DOWNLOAD_READY/final.mp4
```

- 해상도: 1080×1920 (9:16 세로)
- 각 장면: 오디오 길이에 맞춰 자동 조정 + 천천히 확대되는 쾄번즈 효과
- 자막: 대본의 `자막` 텍스트가 하단에 박스와 함께 표시

---

## 옵션 전체 목록

| 옵션 | 필수 | 설명 |
|---|---|---|
| `--project` | ✅ | 프로젝트 폴더 경로 |
| `--bgm` | 선택 | 배경음악 파일 (자동 루프) |
| `--bgm-volume` | 선택 | 배경음악 볼륨 (기본 0.15) |
| `--font` | 선택 | 자막 폰트 경로 직접 지정 |

---

## 자주 발생하는 상황

**"FFmpeg가 설치되어 있지 않습니다"**
→ 위 1번 설치 안내 참고

**"script.json이 없습니다"**
→ 앱에서 대본 생성 후 내보내기 버튼을 먼저 눌러야 합니다

**자막이 안 보임**
→ 한글 폰트를 못 찾은 경우입니다. `--font` 옵션으로 직접 지정하세요
   (Windows: `C:/Windows/Fonts/malgun.ttf`)

**일부 장면만 이미지/음성이 있어도 되나요?**
→ 됩니다. 없는 장면은 자동으로 대체되어 전체 진행에 문제없습니다.
