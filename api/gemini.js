// 시도 순서: gemini-2.5-flash-lite → gemini-2.5-flash → gemini-3.5-flash
const MODELS = [
  "gemini-2.5-flash-lite",
  "gemini-2.5-flash",
  "gemini-3.5-flash",
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function callGemini(apiKey, prompt, model) {
  const r = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
    }
  );
  const data = await r.json();

  if (!r.ok || data.error) {
    throw new Error(data.error?.message || `HTTP ${r.status}`);
  }
  return data.candidates?.[0]?.content?.parts?.[0]?.text || "";
}

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "POST만 허용됩니다" });

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) return res.status(500).json({ error: "GEMINI_API_KEY 환경변수가 없습니다" });

  const { prompt } = req.body;
  if (!prompt) return res.status(400).json({ error: "prompt가 없습니다" });

  let lastError = "";

  // 모델별 순서대로 시도 (각 모델 최대 2회 재시도)
  for (const model of MODELS) {
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const text = await callGemini(apiKey, prompt, model);
        if (text) {
          // 성공 — 어떤 모델로 성공했는지 로그
          console.log(`Gemini 성공: ${model} (시도 ${attempt})`);
          return res.status(200).json({ text, model });
        }
      } catch (e) {
        lastError = e.message;
        console.warn(`Gemini 실패: ${model} 시도${attempt} — ${e.message}`);
        // 429(과부하) 또는 503이면 잠깐 대기 후 다음 시도
        if (e.message.includes("high demand") || e.message.includes("429") || e.message.includes("503")) {
          await sleep(attempt * 1500);
          continue;
        }
        // 다른 오류(404 등)면 즉시 다음 모델로
        break;
      }
    }
  }

  return res.status(503).json({ error: `모든 모델 실패: ${lastError}` });
}
