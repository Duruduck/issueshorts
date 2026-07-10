// Vercel 서버리스 함수 — Pexels 이미지 검색 프록시
// 실사진 자동 수집용 (상업적 사용 무료, 저작자 표시 권장)
// 환경변수: PEXELS_API_KEY (https://www.pexels.com/api/ 에서 무료 발급)

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "POST만 허용됩니다" });

  const apiKey = process.env.PEXELS_API_KEY;
  if (!apiKey) return res.status(500).json({ error: "PEXELS_API_KEY 환경변수가 없습니다" });

  try {
    const { query, count = 6 } = req.body;
    if (!query) return res.status(400).json({ error: "query가 없습니다" });

    const r = await fetch(
      `https://api.pexels.com/v1/search?query=${encodeURIComponent(query)}&per_page=${count}&orientation=portrait`,
      { headers: { Authorization: apiKey } }
    );

    const data = await r.json();
    if (!r.ok) {
      return res.status(r.status).json({ error: data.error || "Pexels API 오류" });
    }

    const photos = (data.photos || []).map((p) => ({
      id: p.id,
      thumbnail: p.src.medium,
      original: p.src.original,
      photographer: p.photographer,
      photographerUrl: p.photographer_url,
      pexelsUrl: p.url,
    }));

    return res.status(200).json({ photos });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
