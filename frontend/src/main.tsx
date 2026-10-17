import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Receipt = { answer: string; mode: string; confidence: number; tool_calls: string[]; path_explanation?: string; receipt: { cypher: string; params: Record<string, unknown>; ms: number; evidence: { node_ids: string[]; edge_ids: string[] }; source_snippets: string[] } };
type Event = { kind: string; text?: string; receipt?: Receipt };

const examples = ["Which team owns the service upstream of Northwind Service 04?", "Who owned Northwind Service 02 on 2024-06-01?", "Trace incident northwind-inc-000 to its decision and author"];

function App() {
  const [tenant, setTenant] = useState("northwind");
  const [question, setQuestion] = useState(examples[0]);
  const [graphOn, setGraphOn] = useState(true);
  const [events, setEvents] = useState<Event[]>([]);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [tab, setTab] = useState("Receipt");
  const [loading, setLoading] = useState(false);
  const [arena, setArena] = useState<any | null>(null);

  useEffect(() => { fetch(`/api/alerts?tenant=${tenant}`).then(r => r.ok ? r.json() : { alerts: [] }).then(d => setAlerts(d.alerts)); }, [tenant]);
  const ask = async () => {
    setLoading(true); setEvents([]); setReceipt(null);
    const response = await fetch("/api/chat", { method: "POST", headers: {"content-type":"application/json"}, body: JSON.stringify({ tenant, question, graph_on: graphOn }) });
    if (!response.ok) { setEvents([{kind:"error", text: "FalkorDB is unavailable. Start docker compose first."}]); setLoading(false); return; }
    const reader = response.body?.getReader(); if (!reader) return;
    const decoder = new TextDecoder(); let buffer = "";
    while (true) { const {value, done} = await reader.read(); if (done) break; buffer += decoder.decode(value); const chunks = buffer.split("\n\n"); buffer = chunks.pop() || ""; chunks.forEach(c => { if (c.startsWith("data: ")) { const e = JSON.parse(c.slice(6)) as Event; setEvents(old => [...old, e]); if (e.receipt) setReceipt(e.receipt); } }); }
    setLoading(false);
  };
  const runArena = async () => { const r = await fetch(`/api/arena/run?tenant=${tenant}`, {method:"POST"}); if (r.ok) setArena(await r.json()); };
  const graphNodes = useMemo(() => receipt?.receipt.evidence.node_ids.slice(0, 8) || [], [receipt]);
  return <div className="shell">
    <header><div className="brand"><span className="mark">✦</span><div><strong>WHYBASE</strong><small>Every answer, with its receipt.</small></div></div><div className="status"><span className="pulse"/> FALKORDB PRIMARY <select value={tenant} onChange={e=>setTenant(e.target.value)}><option value="northwind">Northwind</option><option value="halcyon">Halcyon</option></select></div></header>
    <main>
      <aside className="left panel"><div className="eyebrow">INVESTIGATION</div><h1>Ask why, not just what.</h1><p className="muted">Three agents coordinate through a tenant-isolated knowledge graph. Every claim is traceable.</p>
      <div className="examples">{examples.map(e=><button key={e} onClick={()=>setQuestion(e)}>{e}</button>)}</div>
      <textarea value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();ask();}}}/>
      <div className="controls"><label className={graphOn?"toggle on":"toggle"}><input type="checkbox" checked={graphOn} onChange={e=>setGraphOn(e.target.checked)}/><span/> Graph ON</label><button className="ask" onClick={ask} disabled={loading}>{loading?"Tracing…":"Investigate ↗"}</button></div><div className="quick-actions"><button onClick={()=>fetch("/api/events",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({tenant,title:"Live operating event",text:"The simulated event changed the service operating context."})}).then(()=>setEvents(old=>[...old,{kind:"tool",text:"Scribe ingested simulated event → Sentinel handoff persisted"}]))}>＋ Simulate event</button><button onClick={()=>fetch("/api/isolation-test").then(r=>r.json()).then(d=>setEvents(old=>[...old,{kind:"receipt",text:d.passed?"Tenant isolation verified":"Isolation test failed"}]))}>◎ Isolation test</button></div>
      <div className="agent-stream"><div className="eyebrow">LIVE TRACE</div>{events.map((e,i)=><div className="trace" key={i}><span className={`dot ${e.kind}`}/><span>{e.text || "Receipt assembled"}</span></div>)}</div></aside>
      <section className="center panel"><div className="section-head"><div><div className="eyebrow">EVIDENCE SUBGRAPH</div><h2>{receipt ? "Connected proof path" : "The graph is waiting"}</h2></div><span className="badge">{graphOn?"CONNECTED":"VECTOR BASELINE"}</span></div><div className="graph">{graphNodes.length ? graphNodes.map((n,i)=><div className="node" style={{left:`${18+i*11}%`,top:`${35+(i%3)*18}%`}} key={n}><span className="node-icon">{i===0?"●":"◇"}</span><b>{n}</b><small>{i===0?"question entity":"evidence hop"}</small></div>) : <div className="empty-graph"><div className="orb">✦</div><p>Ask a multi-hop question to animate its evidence path.</p></div>}{graphNodes.slice(1).map((n,i)=><div className="edge" style={{left:`${25+i*11}%`,top:`${48+(i%2)*5}%`,width:"10%"}} key={`e-${n}`}/>)}</div><div className="graph-footer"><span><i className="legend live"/>Evidence nodes</span><span><i className="legend dim"/>Non-evidence dimmed</span><span>{receipt?.receipt.ms ?? "—"} ms query</span></div></section>
      <aside className="right panel"><div className="tabs">{["Receipt","Memory","Agents","Alerts","Arena"].map(t=><button className={tab===t?"active":""} onClick={()=>setTab(t)} key={t}>{t}{t==="Alerts"&&alerts.length>0?<em>{alerts.length}</em>:null}</button>)}</div>{tab==="Receipt"&&<div className="content">{receipt?<><div className="confidence"><span>CONFIDENCE</span><strong>{Math.round(receipt.confidence*100)}%</strong></div><h2>{receipt.answer}</h2><p className="muted">{receipt.path_explanation}</p><div className="eyebrow">CYPHER RECEIPT</div><pre>{receipt.receipt.cypher}</pre><div className="eyebrow">EVIDENCE IDS</div><div className="chips">{receipt.receipt.evidence.node_ids.map(n=><span key={n}>{n}</span>)}</div><div className="eyebrow">SOURCE SNIPPETS</div>{receipt.receipt.source_snippets.map(s=><blockquote key={s}>{s}</blockquote>)}</>:<div className="empty">No receipt yet. The point of WHYBASE is that an answer without evidence is not an answer.</div>}</div>}{tab==="Memory"&&<div className="content"><div className="memory-card"><span>EPISODIC</span><strong>Last investigation</strong><p>Question and tool trace are stored as graph episodes.</p></div><div className="memory-card"><span>PROCEDURAL</span><strong>Dependency investigation</strong><p>Procedures are written to mem_{tenant} after successful investigations.</p></div><div className="memory-card"><span>SEMANTIC</span><strong>Graph facts</strong><p>Contradictions stay visible; stale facts decay instead of disappearing.</p></div></div>}{tab==="Agents"&&<div className="content"><div className="lane"><b>SCRIBE</b><span>ingest → extract → handoff</span></div><div className="lane"><b>ANALYST</b><span>plan → query → receipt</span></div><div className="lane"><b>SENTINEL</b><span>alert → investigate → action</span></div></div>}{tab==="Alerts"&&<div className="content">{alerts.length?alerts.map(a=><div className="alert" key={a.id}><span className="severity">HIGH</span><strong>{a.type}</strong><p>{a.service} has a single active owner.</p><button>Investigate</button><button className="approve" onClick={()=>fetch("/api/alerts/approve",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({tenant,action_id:`${a.id}-action`})}).then(()=>setAlerts(old=>old.filter(x=>x.id!==a.id)))}>Approve action</button></div>):<div className="empty">No open Sentinel alerts.</div>}</div>}{tab==="Arena"&&<div className="content"><h2>Graph ON vs Graph OFF</h2><p className="muted">Same questions, same corpus, different retrieval substrate.</p><button className="ask" onClick={runArena}>Run Arena</button>{arena&&<div className="arena-score"><strong>{Math.round(arena.graph_accuracy*100)}%</strong><span>graph accuracy</span><strong>{Math.round(arena.vector_accuracy*100)}%</strong><span>vector accuracy</span></div>}</div>}</aside>
    </main><footer><span>ⓘ Synthetic public dataset · tenant isolation enforced · MCP-ready</span><span>FalkorDB graph is required for connected proof</span></footer>
  </div>
}
createRoot(document.getElementById("root")!).render(<App />);
