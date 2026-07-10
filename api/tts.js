// Vercel 서버리스 함수 — TTS 음성 생성
// Microsoft Edge Read Aloud API 사용 (완전 무료, API 키 불필요)
// 패키지: msedge-tts (package.json에 등록 필요)

import { MsEdgeTTS, OUTPUT_FORMAT } from "msedge-tts";

// 한국어 뉴럴 음성 (Microsoft Azure/Edge 표준 보이스)
const VOICE_MAP = {
  female: "ko-KR-SunHiNeural",   // 여성 - 차분하고 또렬한 톤
  male:   "ko-KR-InJoonNeural",  // 남성 - 안정적인 내레이션 톤
};

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "POST만 허용됩니다" });
  }

  try {
    const { text, voice = "female", rate = "0%" } = req.body;
    if (!text || !text.trim()) {
      return res.status(400).json({ error: "text가 없습니다" });
    }

    const voiceName = VOICE_MAP[voice] || VOICE_MAP.female;

    const tts = new MsEdgeTTS();
    await tts.setMetadata(voiceName, OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);

    const { audioStream } = tts.toStream(text, { rate });

    const chunks = [];
    for await (const chunk of audioStream) {
      chunks.push(chunk);
    }
    const buffer = Buffer.concat(chunks);

    if (buffer.length === 0) {
      return res.status(500).json({ error: "음성 생성 실패 - 빈 오디오" });
    }

    res.setHeader("Content-Type", "audio/mpeg");
    res.setHeader("Cache-Control", "no-store");
    return res.status(200).send(buffer);
  } catch (e) {
    console.error("[TTS] 오류:", e.message);
    return res.status(500).json({ error: e.message || "TTS 생성 실패" });
  }
}
