import { useState, useEffect } from "react";

const C = {
  bg:"#080A0F", s1:"#0F1118", s2:"#161A24", border:"#1C2133",
  accent:"#FF2D55", blue:"#0A84FF", green:"#30D158", amber:"#FFD60A",
  text:"#E8E8F8", sub:"#6E6E82", dim:"#2A2D3A",
};

const TYPES = {
  all:      { label:"전체",        emoji:"🔥", color:C.sub    },
  kpop:     { label:"K-pop/연예",  emoji:"🎤", color:C.accent },
  social:   { label:"사회/인물",   emoji:"📰", color:C.amber  },
  culture:  { label:"한식/문화",   emoji:"🍜", color:C.green  },
  overseas: { label:"해외 이슈",   emoji:"🌐", color:C.blue   },
  beauty:   { label:"뷰티/패션",   emoji:"💄", color:"#BF5AF2" },
  living:   { label:"생활용품/주방",emoji:"🏠", color:"#FF9F0A" },
  season:   { label:"시즌아이템",  emoji:"🌸", color:"#32ADE6" },
};

const STRUCTURES = {
  kpop:     ["훅: 충격 사실 제시","발견 경로 설명","팬/커뮤니티 반응","인물·제품 핵심","화제 포인트 1","화제 포인트 2","현재 상황/결말","CTA: 댓글 유도"],
  social:   ["훅: 실화임?","배경 설명","사건 전개 1","사건 전개 2","사건 전개 3","반전 or 핵심","의미·파장","CTA: 저장 유도"],
  culture:  ["훅: 해외서 난리남","어느 나라·채널","포인트 1","포인트 2","포인트 3","포인트 4","한국인 반응","CTA: 공감 유도"],
  overseas: ["훅: 이슈 제시","30초 요약","배경 설명","전개 1","전개 2","전개 3","한국 연관성","CTA: 관심 유도"],
  beauty:   ["훅: 이거 써보고 충격받음","제품 소개 (브랜드/가격)","효과·특징 1","효과·특징 2","효과·특징 3","실사용 후기","주의사항 or 대안","CTA: 저장 유도"],
  living:   ["훅: 이걸로 다 해결됨","문제 상황 제시","제품 소개","기능 1","기능 2","가격·구매처","실사용 팁","CTA: 저장 유도"],
  season:   ["훅: 지금 이 시즌에 필수","시즌 이유 설명","아이템 1 소개","아이템 2 소개","아이템 3 소개","가격·할인 정보","품절 urgency","CTA: 저장 유도"],
};

// ── 수집 시간 → 경과 시간 실시간 계산 ──────────────────────
function formatAgo(collectedAt) {
  if (!collectedAt) return "오늘";
  try {
    const dt = new Date(collectedAt.replace(" ", "T"));
    const mins = Math.floor((Date.now() - dt.getTime()) / 60000);
    if (mins < 1)  return "방금 전";
    if (mins < 60) return `${mins}분 전`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}시간 전`;
    return `${Math.floor(hours / 24)}일 전`;
  } catch { return "오늘"; }
}

function buildPrompt(topic, opts) {
  const struct = (STRUCTURES[topic.type] || STRUCTURES.overseas).slice(0, Number(opts.scenes));
  return `당신은 한국 유튜브 쇼츠 대본 전문 작가입니다.\n\n주제: ${topic.title}\n유형: ${TYPES[topic.type]?.label} | 톤: ${opts.tone} | 목표: ${opts.goal} | 훅: ${opts.hook}형\n장면 수: ${opts.scenes}개 | 길이: ${opts.duration}\n\n[장면 구조]\n${struct.map((s,i) => `장면${i+1}: ${s}`).join('\n')}\n\n[출력 형식 - 반드시 이 형식만 사용]\n장면1\n자막: (15자 이내)\n나레이션: (구어체, ${opts.duration==="30초"?"1~2문장":"2~3문장"})\n\n장면2\n자막: ...\n나레이션: ...\n\n규칙: 훅은 첫 1.5초에 시청자를 멈추게 할 것. 전체 낭독 ${opts.duration==="30초"?"25~35":"50~60"}초. 마크다운 기호 없이 순수 텍스트만.`;
}

function buildImagePrompts(topic, count, opts) {
  const style = opts.imageStyle==="실사 사진형" ? "photorealistic editorial photography" : "flat design vector illustration";
  const color = {"밝고 경쾌한":"bright vibrant warm","다크·심플":"dark minimal monochrome","파스텔":"soft pastel dreamy"}[opts.imageColor] || "bright vibrant";
  const txt = opts.imageText==="자막 포함" ? "space for Korean subtitle at bottom" : "no text pure visual";
  return Array.from({length:count},(_,i)=>
    `[장면 ${i+1}]\n${style}, ${color} palette, ${txt}, vertical 9:16\nVisual: ${topic.title} scene ${i+1}\nMood: ${TYPES[topic.type]?.label} Korean Shorts content`
  );
}

function parseScenes(text, count) {
  const scenes = [];
  const blocks = text.split(/(?=\n?장면\d+\n)/);
  for (const b of blocks) {
    const n = b.match(/장면(\d+)/); if (!n) continue;
    const sub = b.match(/자막:\s*(.+)/);
    const nar = b.match(/나레이션:\s*([\s\S]+?)(?=\n장면|\n자막|$)/);
    scenes.push({ num:parseInt(n[1]), subtitle:sub?.[1]?.trim()||"", naration:nar?.[1]?.trim().replace(/\n/g," ")||"" });
  }
  return scenes.slice(0,count).sort((a,b)=>a.num-b.num);
}

function buildUpload(topic) {
  const t = TYPES[topic.type];
  const core = topic.title.slice(0, 20);
  return {
    titles:[
      { label:"정보형",   color:C.blue,   text:`${t?.emoji} ${core} | 무슨 일이 있었나` },
      { label:"감정공감형", color:C.accent, text:`${t?.emoji} 한국인도 몰랐던 ${core}` },
      { label:"궁금증형",  color:C.amber,  text:`${t?.emoji} ${core}, 다들 이거 때문에 난리남` },
    ],
    desc:`${topic.title}\n\n매일 국내외 화제 이슈를 60초로 정리합니다.\n\n#쇼츠 #Shorts #${topic.type==="kpop"?"K팝 #아이돌":topic.type==="culture"?"한식 #K푸드":topic.type==="overseas"?"해외이슈 #글로벌":"사회이슈 #이슈"} #viral`,
    pin:`🔔 매일 이슈 정리 → 구독하면 놓치지 않아요\n💬 여러분 생각은? 댓글로 알려주세요`,
  };
}

const STATUS_C = {"대기중":C.sub,"촬영중":C.amber,"완료":C.green};
const cp = t => navigator.clipboard.writeText(t).catch(()=>{});

const Pill = ({active,color,onClick,children}) => (
  <button onClick={onClick} style={{background:active?color+"20":"transparent",border:`1px solid ${active?color:C.border}`,color:active?color:C.sub,borderRadius:20,padding:"4px 13px",cursor:"pointer",fontSize:12,fontWeight:active?700:400}}>{children}</button>
);
const Card = ({children,style={}}) => (
  <div style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:10,padding:"13px 14px",...style}}>{children}</div>
);
const Lbl = ({children}) => (
  <div style={{fontSize:10,color:C.sub,fontWeight:700,textTransform:"uppercase",letterSpacing:"0.07em",marginBottom:8}}>{children}</div>
);
const OptCard = ({title,children}) => (<Card style={{marginBottom:8}}><Lbl>{title}</Lbl>{children}</Card>);
const Chips = ({opts,val,onChange}) => (
  <div style={{display:"flex",gap:5,flexWrap:"wrap"}}>
    {opts.map(o=>(<button key={o} onClick={()=>onChange(o)} style={{background:val===o?C.accent+"22":"transparent",border:`1px solid ${val===o?C.accent:C.border}`,color:val===o?C.accent:C.sub,borderRadius:6,padding:"4px 10px",cursor:"pointer",fontSize:11,fontWeight:val===o?700:400}}>{o}</button>))}
  </div>
);
const Tag = ({color,children}) => (<span style={{background:color+"20",color,fontSize:9,fontWeight:700,padding:"1px 6px",borderRadius:4}}>{children}</span>);
const OutBlock = ({title,text,children}) => (
  <div style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:10,padding:"12px 14px",marginBottom:10}}>
    <div style={{display:"flex",justifyContent:"space-between",marginBottom:10}}>
      <span style={{fontSize:10,color:C.sub,fontWeight:700,textTransform:"uppercase",letterSpacing:"0.06em"}}>{title}</span>
      <button onClick={()=>cp(text)} style={{background:"none",border:`1px solid ${C.border}`,color:C.sub,borderRadius:5,padding:"2px 8px",cursor:"pointer",fontSize:10}}>복사</button>
    </div>
    {children}
  </div>
);

export default function App() {
  const [tab, setTab] = useState("trends");
  const [typeF, setTypeF] = useState("all");
  const [srcF, setSrcF] = useState("전체");
  const [topic, setTopic] = useState(null);
  const [outTab, setOutTab] = useState("script");
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState(null);
  const [queue, setQueue] = useState([]);
  const [regenIdx, setRegenIdx] = useState(null);
  const [directInput, setDirectInput] = useState("");
  const [directType, setDirectType] = useState("kpop");
  const [editText, setEditText] = useState({});
  const [opts, setOpts] = useState({
    tone:"정보형", goal:"시청지속률", hook:"충격형", scenes:8, duration:"60초",
    model:"Claude", imageStyle:"실사 사진형", imageColor:"밝고 경쾌한", imageText:"자막 포함",
  });
  const setOpt = (k,v) => setOpts(p=>({...p,[k]:v}));
  const [topics, setTopics] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(true);
  const [topicsError, setTopicsError] = useState(null);

  useEffect(() => {
    fetch("/topics.json")
      .then(r => { if (!r.ok) throw new Error("topics.json 로드 실패"); return r.json(); })
      .then(data => { setTopics(data); setTopicsLoading(false); })
      .catch(e => { setTopicsError(e.message); setTopicsLoading(false); });
  }, []);

  const filtered = topics.filter(m=>(typeF==="all"||m.type===typeF)&&(srcF==="전체"||m.source===srcF));
  const pickTopic = t => { setTopic(t); setOutput(null); setTab("generate"); };
  const submitDirect = () => {
    const title = directInput.trim(); if (!title) return;
    pickTopic({ id:Date.now(), type:directType, title, source:"직접입력", from:"직접입력", collected_at:new Date().toISOString(), heat:100 });
    setDirectInput("");
  };

  const callAI = async (prompt) => {
    if (opts.model==="Claude") {
      const r = await fetch("/api/claude",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt})});
      const d = await r.json();
      if (!r.ok) throw new Error(d.error||("오류 "+r.status));
      if (!d.text) throw new Error("빈 응답");
      return d.text;
    } else {
      const r = await fetch("/api/gemini",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt})});
      const d = await r.json();
      if (!r.ok) throw new Error(d.error||("오류 "+r.status));
      return d.text||"";
    }
  };

  const generate = async () => {
    if (!topic) return;
    setLoading(true); setOutput(null);
    try {
      const raw = await callAI(buildPrompt(topic, opts));
      const scenes = parseScenes(raw, Number(opts.scenes));
      setOutput({ raw, scenes, images:buildImagePrompts(topic, Number(opts.scenes), opts), upload:buildUpload(topic) });
      setOutTab("script");
    } catch(e) { setOutput({error:e.message}); }
    finally { setLoading(false); }
  };

  const regenScene = async (idx) => {
    if (!output?.scenes?.[idx]) return;
    const instr = (editText[idx]||"").trim();
    if (!instr) { alert("수정 지시를 입력하세요"); return; }
    const cur = output.scenes[idx];
    setRegenIdx(idx);
    try {
      const prompt = `당신은 한국 유튜브 쇼츠 대본 작가입니다.\n주제: ${topic.title}\n장면 ${idx+1} 현재 내용:\n자막: ${cur.subtitle}\n나레이션: ${cur.naration}\n\n수정 지시: ${instr}\n\n[출력 형식]\n자막: (15자 이내)\n나레이션: (구어체 ${opts.duration==="30초"?"1~2문장":"2~3문장"})\n\n순수 텍스트만.`;
      const raw = await callAI(prompt);
      const sub = raw.match(/자막:\s*(.+)/);
      const nar = raw.match(/나레이션:\s*([\s\S]+)/);
      const updated = {...cur, subtitle:sub?.[1]?.trim()||cur.subtitle, naration:nar?.[1]?.trim().replace(/\n/g," ")||cur.naration};
      setOutput(o=>({...o, scenes:o.scenes.map((s,i)=>i===idx?updated:s)}));
      setEditText(e=>({...e,[idx]:""}));
    } catch(e) { alert("재생성 실패: "+e.message); }
    finally { setRegenIdx(null); }
  };

  const addQueue = () => {
    if (!topic) return;
    setQueue(p=>[{id:Date.now(),topic,status:"대기중",at:new Date().toLocaleTimeString("ko-KR")},...p]);
  };

  return (
    <div style={{background:C.bg,minHeight:"100vh",color:C.text,fontFamily:"'Apple SD Gothic Neo','Malgun Gothic',sans-serif",fontSize:13}}>
      <nav style={{background:C.s1,borderBottom:`1px solid ${C.border}`,padding:"0 20px",position:"sticky",top:0,zIndex:10}}>
        <div style={{maxWidth:960,margin:"0 auto",display:"flex",alignItems:"center",height:48,gap:4}}>
          <div style={{fontWeight:900,fontSize:15,letterSpacing:"-0.03em",marginRight:20,color:C.text}}><span style={{color:C.accent}}>●</span> ISSUESHORTS</div>
          {[["trends","🔥 이슈"],["generate","✏️ 대본"],["queue",`📋 큐${queue.length?` (${queue.length})`:""}`]].map(([k,l])=>(
            <button key={k} onClick={()=>setTab(k)} style={{background:"none",border:"none",cursor:"pointer",padding:"0 14px",height:"100%",color:tab===k?C.text:C.sub,fontWeight:tab===k?700:400,fontSize:13,borderBottom:tab===k?`2px solid ${C.accent}`:"2px solid transparent"}}>{l}</button>
          ))}
        </div>
      </nav>
      <div style={{maxWidth:960,margin:"0 auto",padding:"20px 20px 80px"}}>
        {tab==="trends" && <>
          {topicsLoading && <div style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:10,padding:"20px",textAlign:"center",color:C.sub,marginBottom:16}}><div style={{fontSize:20,marginBottom:6}}>⏳</div>이슈 불러오는 중...</div>}
          {topicsError && <div style={{background:"#1A0508",border:`1px solid ${C.accent}44`,borderRadius:10,padding:"14px 16px",marginBottom:16,color:C.accent,fontSize:13}}>⚠️ {topicsError} — 직접 입력창을 이용해주세요</div>}
          {!topicsLoading && !topicsError && topics.length===0 && <div style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:10,padding:"20px",textAlign:"center",color:C.sub,marginBottom:16}}><div style={{fontSize:20,marginBottom:6}}>📭</div>오늘 수집된 이슈가 없습니다 — 아래에서 직접 입력하세요</div>}
          <div style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:10,padding:"12px 14px",marginBottom:16}}>
            <div style={{fontSize:10,color:C.sub,fontWeight:700,textTransform:"uppercase",letterSpacing:"0.07em",marginBottom:8}}>수집 목록에 없는 주제 직접 입력</div>
            <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
              <div style={{display:"flex",gap:5,flexWrap:"wrap",marginBottom:6,width:"100%"}}>
                {Object.entries(TYPES).filter(([k])=>k!=="all").map(([k,t])=>(
                  <button key={k} onClick={()=>setDirectType(k)} style={{background:directType===k?t.color+"22":"transparent",border:`1px solid ${directType===k?t.color:C.border}`,color:directType===k?t.color:C.sub,borderRadius:6,padding:"3px 10px",cursor:"pointer",fontSize:11,fontWeight:directType===k?700:400}}>{t.emoji} {t.label}</button>
                ))}
              </div>
              <input placeholder="예: 전소미 데오드란트, 늑구 탈출, 한식 틱톡 바이럴..." value={directInput} onChange={e=>setDirectInput(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")submitDirect();}} style={{flex:1,background:C.s1,border:`1px solid ${C.border}`,borderRadius:7,padding:"8px 12px",color:C.text,fontSize:13,minWidth:200}}/>
              <button onClick={submitDirect} disabled={!directInput.trim()} style={{background:directInput.trim()?C.accent:C.dim,border:"none",color:directInput.trim()?"#fff":C.sub,borderRadius:7,padding:"8px 16px",cursor:directInput.trim()?"pointer":"not-allowed",fontWeight:700,fontSize:13,whiteSpace:"nowrap"}}>대본 생성 →</button>
            </div>
          </div>
          <div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:16}}>
            {Object.entries(TYPES).map(([k,t])=>(<Pill key={k} active={typeF===k} color={t.color} onClick={()=>setTypeF(k)}>{t.emoji} {t.label}</Pill>))}
            <div style={{marginLeft:"auto",display:"flex",gap:6}}>{["전체","해외","국내"].map(s=>(<Pill key={s} active={srcF===s} color={C.blue} onClick={()=>setSrcF(s)}>{s}</Pill>))}</div>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))",gap:10}}>
            {filtered.map(m=>{ const t=TYPES[m.type]; const sel=topic?.id===m.id; return (
              <div key={m.id} onClick={()=>pickTopic(m)} style={{background:sel?t.color+"18":C.s2,border:`1px solid ${sel?t.color:C.border}`,borderRadius:10,padding:"14px 16px",cursor:"pointer"}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:8}}>
                  <span style={{background:t.color+"20",color:t.color,fontSize:10,fontWeight:700,padding:"2px 8px",borderRadius:10}}>{t.emoji} {t.label}</span>
                  <span style={{fontSize:10,color:C.sub}}>{formatAgo(m.collected_at)}</span>
                </div>
                <div style={{fontWeight:600,lineHeight:1.5,marginBottom:10,fontSize:13}}>{m.title}</div>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <span style={{fontSize:10,color:C.sub}}>{m.source} · {m.from}</span>
                  <div style={{display:"flex",alignItems:"center",gap:5}}>
                    <div style={{width:36,height:3,background:C.dim,borderRadius:2}}><div style={{width:`${m.heat}%`,height:"100%",background:t.color,borderRadius:2}}/></div>
                    <span style={{fontSize:10,color:t.color,fontWeight:800}}>{m.heat}</span>
                  </div>
                </div>
              </div>
            );})}
          </div>
        </>}

        {tab==="generate" && (
          <div style={{display:"grid",gridTemplateColumns:topic?"300px 1fr":"1fr",gap:16,alignItems:"start"}}>
            <div>
              <Card style={{marginBottom:10}}>
                <Lbl>선택된 이슈</Lbl>
                {topic ? <>
                  <div style={{color:TYPES[topic.type]?.color,fontSize:10,fontWeight:700,marginBottom:4}}>{TYPES[topic.type]?.emoji} {TYPES[topic.type]?.label}</div>
                  <div style={{fontWeight:600,lineHeight:1.5,fontSize:13,marginBottom:10}}>{topic.title}</div>
                  <button onClick={()=>{setTopic(null);setTab("trends");}} style={{background:"none",border:`1px solid ${C.border}`,color:C.sub,borderRadius:6,padding:"3px 10px",cursor:"pointer",fontSize:11}}>다른 이슈 선택</button>
                </> : <>
                  <div style={{color:C.sub,fontSize:12,marginBottom:10}}>선택된 이슈가 없습니다</div>
                  <button onClick={()=>setTab("trends")} style={{background:C.accent+"22",border:`1px solid ${C.accent}`,color:C.accent,borderRadius:6,padding:"5px 14px",cursor:"pointer",fontSize:12,fontWeight:700}}>이슈 선택하기 →</button>
                </>}
              </Card>
              {topic && <>
                <OptCard title="톤"><Chips opts={["정보형","유머·놀람형","진지·해설형"]} val={opts.tone} onChange={v=>setOpt("tone",v)}/></OptCard>
                <OptCard title="목표"><Chips opts={["시청지속률","저장 유도","댓글 유도","공유 유도"]} val={opts.goal} onChange={v=>setOpt("goal",v)}/></OptCard>
                <OptCard title="훅 스타일"><Chips opts={["질문형","충격형","공감형"]} val={opts.hook} onChange={v=>setOpt("hook",v)}/></OptCard>
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
                  <OptCard title="장면 수"><Chips opts={[6,8,10]} val={opts.scenes} onChange={v=>setOpt("scenes",v)}/></OptCard>
                  <OptCard title="길이"><Chips opts={["30초","60초"]} val={opts.duration} onChange={v=>setOpt("duration",v)}/></OptCard>
                </div>
                <OptCard title="이미지 스타일"><Chips opts={["실사 사진형","플랫 일러스트"]} val={opts.imageStyle} onChange={v=>setOpt("imageStyle",v)}/></OptCard>
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
                  <OptCard title="색감"><Chips opts={["밝고 경쾌한","다크·심플","파스텔"]} val={opts.imageColor} onChange={v=>setOpt("imageColor",v)}/></OptCard>
                  <OptCard title="텍스트"><Chips opts={["자막 포함","텍스트 없음"]} val={opts.imageText} onChange={v=>setOpt("imageText",v)}/></OptCard>
                </div>
                <OptCard title="AI 모델"><Chips opts={["Claude","Gemini"]} val={opts.model} onChange={v=>setOpt("model",v)}/></OptCard>
                <button onClick={generate} disabled={loading} style={{width:"100%",background:loading?C.dim:C.accent,border:"none",color:"#fff",borderRadius:10,padding:"12px",fontWeight:800,fontSize:14,cursor:loading?"not-allowed":"pointer"}}>{loading?"생성 중…":"✨  대본 생성"}</button>
              </>}
            </div>
            {topic && (
              <div>
                {!output && !loading && <div style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:12,padding:60,textAlign:"center",color:C.sub}}><div style={{fontSize:36,marginBottom:12}}>✨</div>옵션 설정 후 대본 생성을 누르세요</div>}
                {loading && <div style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:12,padding:60,textAlign:"center",color:C.sub}}><div style={{fontSize:32,marginBottom:12}}>⏳</div>{opts.model}가 대본 작성 중…</div>}
                {output?.error && <div style={{background:"#1A0508",border:`1px solid ${C.accent}44`,borderRadius:12,padding:20,color:C.accent}}>오류: {output.error}</div>}
                {output && !output.error && <>
                  <div style={{display:"flex",gap:8,marginBottom:12,flexWrap:"wrap"}}>
                    {[["script","📝 대본"],["image","🎨 이미지 프롬프트"],["upload","📤 업로드 패키지"]].map(([k,l])=>(
                      <button key={k} onClick={()=>setOutTab(k)} style={{background:outTab===k?C.accent+"22":C.s1,border:`1px solid ${outTab===k?C.accent:C.border}`,color:outTab===k?C.accent:C.sub,borderRadius:8,padding:"6px 14px",cursor:"pointer",fontSize:12,fontWeight:outTab===k?700:400}}>{l}</button>
                    ))}
                    <button onClick={addQueue} style={{marginLeft:"auto",background:C.green+"15",border:`1px solid ${C.green}44`,color:C.green,borderRadius:8,padding:"6px 14px",cursor:"pointer",fontSize:12,fontWeight:700}}>+ 큐 추가</button>
                  </div>
                  {outTab==="script" && <>
                    {(output.scenes?.length>0?output.scenes:[]).map((s,i)=>(
                      <div key={i} style={{background:C.s2,border:`1px solid ${regenIdx===i?C.amber:C.border}`,borderRadius:10,padding:"12px 14px",marginBottom:8}}>
                        <div style={{display:"flex",gap:6,marginBottom:8,alignItems:"center"}}>
                          <span style={{fontSize:10,color:C.accent,fontWeight:800}}>장면 {s.num||i+1}</span>
                          {i===0 && <Tag color={C.accent}>훅</Tag>}
                          {i===(output.scenes.length-1) && <Tag color={C.blue}>CTA</Tag>}
                        </div>
                        {s.subtitle && <div style={{fontWeight:700,fontSize:15,marginBottom:6}}>{s.subtitle}</div>}
                        <div style={{color:C.sub,lineHeight:1.65,fontSize:13,marginBottom:10}}>{s.naration}</div>
                        <div style={{display:"flex",gap:6,alignItems:"center"}}>
                          <input placeholder="이 장면 수정 지시 (예: 더 충격적으로)" value={editText[i]||""} disabled={regenIdx!==null} onChange={e=>setEditText(p=>({...p,[i]:e.target.value}))} onKeyDown={e=>{if(e.key==="Enter")regenScene(i);}} style={{flex:1,background:C.s1,border:`1px solid ${C.border}`,borderRadius:6,padding:"5px 9px",color:C.text,fontSize:11,boxSizing:"border-box"}}/>
                          <button onClick={()=>regenScene(i)} disabled={regenIdx!==null} style={{background:regenIdx===i?C.dim:C.amber+"22",border:`1px solid ${C.amber}55`,color:C.amber,borderRadius:6,padding:"5px 10px",cursor:regenIdx!==null?"not-allowed":"pointer",fontSize:11,fontWeight:700,whiteSpace:"nowrap"}}>{regenIdx===i?"⏳":"🔄"}</button>
                        </div>
                      </div>
                    ))}
                    {output.scenes?.length===0 && <div style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:10,padding:16}}><pre style={{whiteSpace:"pre-wrap",lineHeight:1.7,fontSize:13,margin:0,color:C.text}}>{output.raw}</pre></div>}
                    <button onClick={()=>cp(output.raw)} style={{width:"100%",background:C.s2,border:`1px solid ${C.border}`,color:C.sub,borderRadius:8,padding:"8px",cursor:"pointer",fontSize:12,marginTop:6}}>전체 대본 복사</button>
                  </>}
                  {outTab==="image" && output.images?.map((p,i)=>(
                    <div key={i} style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:10,padding:"12px 14px",marginBottom:8}}>
                      <div style={{display:"flex",justifyContent:"space-between",marginBottom:8}}>
                        <span style={{fontSize:10,color:C.blue,fontWeight:700}}>장면 {i+1}</span>
                        <button onClick={()=>cp(p)} style={{background:"none",border:`1px solid ${C.border}`,color:C.sub,borderRadius:5,padding:"2px 8px",cursor:"pointer",fontSize:10}}>복사</button>
                      </div>
                      <div style={{fontSize:12,color:C.sub,lineHeight:1.6,whiteSpace:"pre-wrap"}}>{p}</div>
                    </div>
                  ))}
                  {outTab==="upload" && output.upload && <>
                    <OutBlock title="제목 후보 3종" text={output.upload.titles.map(t=>`[${t.label}] ${t.text}`).join('\n')}>
                      {output.upload.titles.map((t,i)=>(
                        <div key={i} style={{padding:"9px 0",borderBottom:i<2?`1px solid ${C.border}`:"none"}}>
                          <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:4}}>
                            <span style={{background:t.color+"22",color:t.color,fontSize:9,fontWeight:700,padding:"1px 7px",borderRadius:4}}>{t.label}</span>
                            <button onClick={()=>cp(t.text)} style={{background:"none",border:"none",color:C.sub,cursor:"pointer",fontSize:10,marginLeft:"auto"}}>복사</button>
                          </div>
                          <div style={{fontSize:13,lineHeight:1.4}}>{t.text}</div>
                        </div>
                      ))}
                    </OutBlock>
                    <OutBlock title="설명문" text={output.upload.desc}><div style={{whiteSpace:"pre-wrap",fontSize:12,color:C.sub,lineHeight:1.7}}>{output.upload.desc}</div></OutBlock>
                    <OutBlock title="핀 댓글" text={output.upload.pin}><div style={{fontSize:13,lineHeight:1.6}}>{output.upload.pin}</div></OutBlock>
                  </>}
                </>}
              </div>
            )}
          </div>
        )}

        {tab==="queue" && <>
          <div style={{fontWeight:700,fontSize:15,marginBottom:16}}>제작 큐 {queue.length>0&&`(${queue.length})`}</div>
          {queue.length===0 ? (
            <div style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:12,padding:60,textAlign:"center",color:C.sub}}><div style={{fontSize:28,marginBottom:8}}>📋</div>대본 생성 후 큐에 추가해보세요</div>
          ) : queue.map(q=>{ const t=TYPES[q.topic.type]; return (
            <div key={q.id} style={{background:C.s2,border:`1px solid ${C.border}`,borderRadius:10,padding:"12px 16px",marginBottom:8,display:"flex",alignItems:"center",gap:12}}>
              <div style={{flex:1}}>
                <div style={{fontSize:10,color:t?.color,fontWeight:700,marginBottom:3}}>{t?.emoji} {t?.label}</div>
                <div style={{fontWeight:600,fontSize:13}}>{q.topic.title}</div>
                <div style={{fontSize:10,color:C.sub,marginTop:2}}>{q.at}</div>
              </div>
              <div style={{display:"flex",gap:5}}>
                {["대기중","촬영중","완료"].map(s=>(
                  <button key={s} onClick={()=>setQueue(p=>p.map(i=>i.id===q.id?{...i,status:s}:i))} style={{background:q.status===s?STATUS_C[s]+"22":"transparent",border:`1px solid ${q.status===s?STATUS_C[s]:C.border}`,color:q.status===s?STATUS_C[s]:C.sub,borderRadius:6,padding:"3px 8px",cursor:"pointer",fontSize:10}}>{s}</button>
                ))}
              </div>
            </div>
          );})}
        </>}
      </div>
    </div>
  );
}
