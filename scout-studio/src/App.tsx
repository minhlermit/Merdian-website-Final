import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CandidateCard } from './components/CandidateCard';
import { DetailPanel } from './components/DetailPanel';
import { Dialog } from './components/Dialog';
import { FAQ } from './components/FAQ';
import { Hero } from './components/Hero';
import { Icon } from './components/Icons';
import { Plans } from './components/Plans';
import { SceneLayer } from './components/SceneLayer';
import { SiteFooter } from './components/SiteFooter';
import { SiteHeader, type NavTarget } from './components/SiteHeader';
import { Story } from './components/Story';
import { SampleMemo } from './components/SampleMemo';
import { WhySection } from './components/WhySection';
import { DataStatus } from './components/DataStatus';
import { BrandCursor, useReveal } from './components/Motion';
import { RunExperience } from './components/RunExperience';
import { WalletPanel } from './components/WalletPanel';
import { GetMC } from './components/GetMC';
import { sceneBridge } from './scene/bridge';
import { clearPayload, fetchLocal, savePayload, savedPayload, validPayload } from './lib/data';
import { countdown, emptyDemo, freshDemo, isCurrent, windowStart } from './lib/cycle';
import { useWallet } from './lib/wallet';
import { money, relativeTime } from './lib/format';
import type { Candidate, ScoutPayload } from './types';
import './style.css';
import './enhancements.css';
import './styles/fonts.css';
import './styles/tokens.css';
import './styles/site.css';

type Filter = 'all' | 'research' | 'watch' | 'risk';
type Sort = 'signal' | 'liquidity' | 'recent';

function download(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function rating(value: string): string {
  return ({RESEARCH_DEEPER:'RESEARCH DEEPER',UNPROVEN:'IDEA / UNPROVEN',SPECULATIVE:'SPECULATIVE',AVOID:'AVOID',UNRATED:'UNRATED',RESEARCH:'RESEARCH',WATCH:'WATCH',CAUTION:'CAUTION'} as Record<string,string>)[value] || value.replace(/_/g,' ');
}

export default function App() {
  const consoleRef = useRef<HTMLElement | null>(null), storyRef = useRef<HTMLElement>(null), plansRef = useRef<HTMLElement>(null), memoRef = useRef<HTMLElement>(null), whyRef = useRef<HTMLElement>(null), faqRef = useRef<HTMLElement>(null), fileRef = useRef<HTMLInputElement>(null);
  const consoleSlot = useCallback((el: HTMLElement | null) => { consoleRef.current = el; sceneBridge.slot('console')(el); }, []);
  const [data,setData] = useState<ScoutPayload>(() => savedPayload() || (localStorage.getItem('scout-demo-cleared-window-v1')===String(windowStart()) ? emptyDemo() : freshDemo()));
  const [bridge,setBridge] = useState(false), [running,setRunning] = useState(false);
  const [query,setQuery] = useState(''), [filter,setFilter] = useState<Filter>('all'), [sort,setSort] = useState<Sort>('signal');
  const [active,setActive] = useState<Candidate|null>(null), [selected,setSelected] = useState<string[]>([]);
  const [compareOpen,setCompareOpen] = useState(false), [reportOpen,setReportOpen] = useState(false), [setupOpen,setSetupOpen] = useState(false);
  const [reportHtml,setReportHtml] = useState<string|null>(null), [notice,setNotice] = useState('');
  const [runOpen,setRunOpen] = useState(false), [walletOpen,setWalletOpen] = useState(false), [mcOpen,setMcOpen] = useState(false);
  const [clock,setClock] = useState(countdown());
  const wallet = useWallet();
  useReveal();
  const scroll = (ref: React.RefObject<HTMLElement|null>) => ref.current?.scrollIntoView({behavior:'smooth',block:'start'});
  const navigate = (target: NavTarget) => scroll({memo:memoRef,why:whyRef,story:storyRef,console:consoleRef,plans:plansRef,faq:faqRef}[target]);

  useEffect(() => {
    // Direct links such as /#console land on the section once the page has rendered.
    const id = decodeURIComponent(window.location.hash.slice(1));
    if (!id) return;
    const frame = requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({block:'start'}));
    return () => cancelAnimationFrame(frame);
  }, []);
  useEffect(() => {
    let disposed = false;
    fetchLocal().then(payload => {
      if (disposed || !payload) return;
      setBridge(true);
      if (!savedPayload() && isCurrent(payload.generated)) setData(payload);
    });
    return () => { disposed = true; };
  }, []);
  useEffect(() => {
    if (!bridge) return;
    const poll = async () => {
      try {
        const status = await fetch('/api/status', {cache:'no-store'}).then(r => r.json());
        setRunning(Boolean(status.running));
        if (!status.running && data.source === 'local') {
          const payload = await fetchLocal(); if (payload && isCurrent(payload.generated)) setData(payload);
        }
      } catch { setBridge(false); }
    };
    poll(); const id = setInterval(poll, 12000); return () => clearInterval(id);
  }, [bridge, data.source]);
  useEffect(() => {
    const id=setInterval(() => {
      setClock(countdown());
      if (!isCurrent(data.generated)) {
        clearPayload();setSelected([]);setActive(null);setQuery('');setFilter('all');setReportHtml(null);
        localStorage.setItem('scout-demo-cleared-window-v1',String(windowStart()));
        setData(emptyDemo());
        setNotice('A new six-hour window started. This board was cleared. Run the local Scout or import a fresh export for current research.');
      }
    },1000);
    return ()=>clearInterval(id);
  },[data.generated]);

  const candidates = useMemo(() => data.candidates.filter(c => {
    const match = `${c.symbol} ${c.name} ${c.pair} ${c.address}`.toLowerCase().includes(query.trim().toLowerCase());
    const category = filter === 'all' || (filter === 'research' && (c.researchStatus === 'COMPLETE' || c.verdict === 'RESEARCH_DEEPER')) ||
      (filter === 'watch' && ['WATCH','QUEUED','INCOMPLETE'].includes(c.researchStatus)) ||
      (filter === 'risk' && ['HIGH','CRITICAL'].includes(c.exitRisk));
    return match && category;
  }).sort((a,b) => sort === 'liquidity' ? (b.liquidity||0)-(a.liquidity||0) : sort === 'recent' ? (b.updated||0)-(a.updated||0) :
    (b.scoreMax ? (b.score||0)/b.scoreMax : 0) - (a.scoreMax ? (a.score||0)/a.scoreMax : 0) || (b.liquidity||0)-(a.liquidity||0)), [data,query,filter,sort]);
  const selectedCandidates = data.candidates.filter(c => selected.includes(c.address));
  const highRisk = data.candidates.filter(c => ['HIGH','CRITICAL'].includes(c.exitRisk)).length;
  const avgLiq = data.candidates.length ? data.candidates.reduce((s,c)=>s+(c.liquidity||0),0) / data.candidates.length : null;

  const importFile = async (file?: File) => {
    if (!file) return;
    if (file.size > 12_000_000) { setNotice('File exceeds the 12 MB import limit.'); return; }
    try {
      const content = await file.text();
      if (file.name.toLowerCase().endsWith('.html')) { setReportHtml(content); setNotice('Investor report imported. Open it with “View report”.'); return; }
      const parsed: unknown = JSON.parse(content);
      if (!validPayload(parsed)) throw new Error('Expected a Stock Scout Studio export (schema 1).');
      if (!isCurrent(parsed.generated)) throw new Error('This export belongs to an earlier six-hour window. Please run Scout and export a fresh board.');
      const incoming: ScoutPayload = {...parsed,source:'export'};
      setData(incoming); savePayload(incoming); setSelected([]); setNotice(`Imported ${incoming.candidates.length} candidates from ${file.name}.`);
    } catch(e) { setNotice(e instanceof Error ? e.message : 'Could not read this file.'); }
    finally { if(fileRef.current) fileRef.current.value=''; }
  };
  const resetData = async () => {
    clearPayload(); setReportHtml(null); setSelected([]);
    const local = bridge ? await fetchLocal() : null;
    setData(local && isCurrent(local.generated) ? local : freshDemo()); setNotice(local && isCurrent(local.generated) ? 'Showing local Scout data.' : 'Showing the fictional demo scenario.');
  };
  const runScout = async () => {
    if (!bridge) { setRunOpen(true); return; }
    try {
      const response = await fetch('/api/run',{method:'POST'});
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'Could not start Scout.');
      setRunning(true); setNotice(body.message);
    } catch(e) { setNotice(e instanceof Error ? e.message : 'Could not start Scout.'); }
  };
  // The sample memo is built from the AURA demo candidate; open its full file while the demo board shows it.
  const sample = data.source==='demo' ? data.candidates.find(c=>c.address==='demo-01') : undefined;
  const openSample = () => { if (sample) setActive(sample); else setRunOpen(true); };
  const openReport = async () => {
    if (!reportHtml && bridge && data.source === 'local' && data.reportAvailable) {
      try { const r = await fetch('/api/report',{cache:'no-store'}); if(r.ok) setReportHtml(await r.text()); }
      catch { setNotice('Could not load latest.html from the local bridge.'); return; }
    }
    setActive(null); setReportOpen(true);
  };

  return <>
    <a className="skip-link" href="#console" onClick={e=>{e.preventDefault();scroll(consoleRef);}}>Skip to the console</a>
    <BrandCursor/>
    <SceneLayer/>
    <SiteHeader onNavigate={navigate} onWallet={()=>setWalletOpen(true)} onGetMC={()=>setMcOpen(true)} onRun={runScout} runLabel={bridge?'Run Scout':'Try demo'} connected={Boolean(wallet.address)} walletLabel={wallet.address?`${wallet.address.slice(0,5)}…${wallet.address.slice(-4)}`:'Connect wallet'}/>
    <main id="main">
      <div className="scene-zone" ref={sceneBridge.slot('zone')}>
        <Hero onMemo={()=>scroll(memoRef)} onRun={runScout} live={bridge}/>
        <SampleMemo sectionRef={memoRef} canOpen={Boolean(sample)} onOpen={openSample} onConsole={()=>scroll(consoleRef)}/>
        <WhySection sectionRef={whyRef}/>
        <Story sectionRef={storyRef} onRun={runScout} onConsole={()=>scroll(consoleRef)} live={bridge}/>
      </div>
      <section className="console-section" id="console" ref={consoleSlot} aria-labelledby="console-title">
        <div className="wrap-wide">
          <div className="console-intro" data-reveal><div><p className="label">The console</p><h2 id="console-title">Less noise.<br/>More signal.</h2></div><p className="section-lede">Start here: scan the board for what changed, open a candidate to read its evidence, then compare up to three side by side before forming a view.</p></div>
          <div className="console-shell">
            <div className="console-topbar"><div className="console-title"><span className="terminal-icon"><Icon name="grid" size={19}/></span><div><strong>SCOUT / CONTROL ROOM</strong><small>ROBINHOOD CHAIN <span>·</span> NETWORK 4663</small></div></div><div className="console-status"><span className={`status-dot ${data.source==='demo'?'demo-dot':''}`}/><span>{data.source==='demo'?'DEMO SCENARIO':data.source==='local'?'LOCAL DATA':'IMPORTED SNAPSHOT'}</span><span className="status-date">{relativeTime(data.generated)}</span></div></div>
            {data.source!=='demo'&&data.warnings.length>0&&<div className="warning-banner"><Icon name="info" size={17}/><span>{data.warnings[0]}{data.warnings.length>1&&` · ${data.warnings.length-1} more data warnings`}</span></div>}
            <div className="summary-grid"><div><span className="summary-symbol">↗</span><small>CANDIDATES TRACKED</small><strong>{String(data.candidates.length).padStart(2,'0')}</strong><span className="summary-foot">Across stock-paired pools</span></div><div><span className="summary-symbol">✳</span><small>SIGNALS RECORDED</small><strong>{String(data.events.length).padStart(2,'0')}</strong><span className="summary-foot">Latest stored events</span></div><div><span className="summary-symbol warn">◉</span><small>HIGH EXIT RISK</small><strong>{String(highRisk).padStart(2,'0')}</strong><span className="summary-foot">Needs extra scrutiny</span></div><div className="summary-accent"><span className="summary-symbol">◇</span><small>AVG. POOL LIQUIDITY</small><strong>{money(avgLiq)}</strong><span className="summary-foot">Observed candidate pools</span></div></div>
            <div className="workspace-toolbar"><div className="workspace-heading"><span>THE WATCHLIST</span><small>{candidates.length.toString().padStart(2,'0')} VISIBLE / {data.candidates.length.toString().padStart(2,'0')} TOTAL</small></div><div className="workspace-actions"><button className="subtle-action" onClick={()=>fileRef.current?.click()}><Icon name="upload" size={16}/> Import</button><button className="subtle-action" onClick={()=>download(`scout-studio-${data.runId||'snapshot'}.json`,JSON.stringify(data,null,2),'application/json')}><Icon name="download" size={16}/> Export</button><button className="run-action" onClick={runScout} disabled={running}><Icon name={running?'refresh':'play'} size={14}/>{running?'SCOUT RUNNING':bridge?'RUN SCOUT':'RUN DEMO'}</button><input hidden ref={fileRef} type="file" accept=".json,.html,application/json,text/html" onChange={e=>importFile(e.target.files?.[0])}/></div></div>
            <DataStatus data={data} bridge={bridge} running={running} clock={clock}/>
            {notice&&<div className="inline-notice" role="status"><span>{notice}</span><button aria-label="Dismiss notice" onClick={()=>setNotice('')}><Icon name="close" size={14}/></button></div>}
            <div className="filter-row"><div className="filter-tabs" role="group" aria-label="Candidate filters">{([['all','All candidates'],['research','Researched'],['watch','Watchlist'],['risk','High risk']] as [Filter,string][]).map(([key,label])=><button key={key} className={filter===key?'active':''} onClick={()=>setFilter(key)}>{label}{key==='risk'&&<span>{highRisk}</span>}</button>)}</div><div className="filter-controls"><label className="search-box"><Icon name="search" size={18}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search token or pair" aria-label="Search token or pair"/></label><label className="sort-box"><Icon name="filter" size={16}/><select value={sort} onChange={e=>setSort(e.target.value as Sort)} aria-label="Sort candidates"><option value="signal">Signal score</option><option value="liquidity">Liquidity</option><option value="recent">Recently updated</option></select><Icon name="chevron" size={15}/></label></div></div>
            {candidates.length ? <div className="candidate-grid">{candidates.map(c=><CandidateCard key={c.address} candidate={c} onOpen={()=>setActive(c)} selected={selected.includes(c.address)} onSelect={()=>setSelected(old=>old.includes(c.address)?old.filter(x=>x!==c.address):old.length<3?[...old,c.address]:old)}/>)}</div> : <div className="empty-state"><img src="/assets/scout-mascot-pixel.png" alt="Scout mascot searching"/><h3>No candidates in this view.</h3><p>{data.candidates.length ? 'Try another filter or search.' : 'Run the local Scout or import a JSON export to populate this console.'}</p></div>}
            <div className="console-lower"><div className="signal-feed"><div className="feed-head"><div><span className="eyebrow-small">EVENT STREAM / 06H CYCLES</span><h3>Latest signals</h3></div><span className="feed-count">{data.events.length.toString().padStart(2,'0')} EVENTS</span></div>{data.events.length ? data.events.slice(0,5).map(e=><button className="signal-row" key={e.id} onClick={()=>{const c=data.candidates.find(c=>c.address===e.token);if(c)setActive(c);}}><span className={`event-indicator ${e.severity>=4?'event-high':''}`}><Icon name={e.severity>=4?'shield':'spark'} size={17}/></span><span className="event-main"><b>{e.type.replace(/_/g,' ')}</b><small>{e.symbol} <i>·</i> {e.detail||'Observed event; cause requires investigation.'}</small></span><time>{relativeTime(e.time)}</time><Icon name="arrowUp" size={16}/></button>) : <div className="feed-empty">No events stored in this snapshot.</div>}</div><div className="protocol-card"><div className="protocol-top"><span>SCOUT PROTOCOL</span><Icon name="spark" size={23}/></div><img src="/assets/signal-orbit-3d.png" alt=""/><div><h3>Every claim<br/>has a trail.</h3><p>Discovery finds the change. Research checks the story. A memo only follows completed evidence review.</p><button onClick={()=>scroll(storyRef)}>Explore the method <Icon name="arrow" size={17}/></button></div></div></div>
            <div className="console-footer"><span><Icon name="shield" size={16}/> RESEARCH ONLY. NO TRADING OR WALLET ACCESS.</span><div>{data.source==='export'&&<button onClick={resetData}>Clear import</button>}{(reportHtml||data.reportAvailable)&&<button onClick={openReport}>View latest report <Icon name="arrowUp" size={14}/></button>}</div></div>
          </div>
        </div>
      </section>
      <Plans sectionRef={plansRef} onConsole={()=>scroll(consoleRef)} onGetMC={()=>setMcOpen(true)}/>
      <FAQ sectionRef={faqRef}/>
    </main>
    <SiteFooter onNavigate={navigate}/>
    {runOpen&&<RunExperience onClose={()=>setRunOpen(false)} onExplore={()=>{setRunOpen(false);localStorage.removeItem('scout-demo-cleared-window-v1');if(data.source==='demo'&&data.candidates.length===0)setData(freshDemo());scroll(consoleRef);}}/>}
    {walletOpen&&<WalletPanel wallet={wallet} onClose={()=>setWalletOpen(false)} onGetMC={()=>setMcOpen(true)}/>}
    {mcOpen&&<GetMC onClose={()=>setMcOpen(false)} onWallet={()=>setWalletOpen(true)} onExplore={()=>{setMcOpen(false);scroll(consoleRef);}} connected={Boolean(wallet.address)}/>}
    {selected.length>0&&<div className="compare-dock"><span><Icon name="layers" size={19}/> {selected.length}/3 selected</span><div className="selected-pills">{selectedCandidates.map(c=><span key={c.address}>{c.symbol}<button onClick={()=>setSelected(old=>old.filter(x=>x!==c.address))} aria-label={`Remove ${c.symbol}`}><Icon name="close" size={12}/></button></span>)}</div><button className="button-primary" onClick={()=>setCompareOpen(true)} disabled={selected.length<2}>Compare <Icon name="arrow" size={16}/></button></div>}
    {active&&<DetailPanel candidate={active} onClose={()=>setActive(null)} onReport={openReport} hasReport={Boolean(reportHtml||data.reportAvailable)}/>}
    {compareOpen&&<Dialog label="Compare candidates" className="modal compare-modal" onClose={()=>setCompareOpen(false)}>{close=><><div className="modal-head"><div><span>RESEARCH SIDE BY SIDE</span><h2>Compare signals.</h2></div><button onClick={close} aria-label="Close comparison"><Icon name="close"/></button></div><div className="compare-table"><div className="compare-labels"><span>TOKEN</span><span>PAIR</span><span>VERDICT</span><span>LIQUIDITY</span><span>24H VOLUME</span><span>HOLDERS</span><span>TOP 10 EOA</span><span>EXIT RISK</span><span>EVIDENCE ITEMS</span></div>{selectedCandidates.map(c=><div className="compare-column" key={c.address}><strong>{c.symbol}<small>{c.name}</small></strong><span>{c.pair}</span><span>{rating(c.verdict)}</span><span>{money(c.liquidity)}</span><span>{money(c.volume24)}</span><span>{c.holders?.toLocaleString()??'—'}</span><span>{c.top10==null?'—':`${c.top10}%`}</span><span className={`risk-text risk-${c.exitRisk.toLowerCase()}`}>{c.exitRisk}</span><span>{c.evidence.length}</span></div>)}</div><p>Scores and risk floors come from the original Scout when local data is connected. Comparisons are research aids, not rankings to buy.</p></>}</Dialog>}
    {reportOpen&&<Dialog label="Investor report" className="modal report-modal" onClose={()=>setReportOpen(false)}>{close=><><div className="modal-head"><div><span>INVESTOR REPORT / {data.runId||'IMPORTED'}</span><h2>Research memo.</h2></div><div className="modal-tools">{reportHtml&&<button onClick={()=>download('stock-scout-investor-report.html',reportHtml,'text/html')}><Icon name="download" size={17}/> Download</button>}<button onClick={close} aria-label="Close report"><Icon name="close"/></button></div></div>{reportHtml?<iframe title="Investor report" srcDoc={reportHtml} sandbox="allow-popups" referrerPolicy="no-referrer"/>:<div className="report-empty"><Icon name="file" size={32}/><h3>No report loaded yet.</h3><p>Import a `latest.html` file from the original Scout to read it here.</p><button className="button-primary" onClick={()=>{close();fileRef.current?.click();}}>Import HTML report <Icon name="upload" size={16}/></button></div>}</>}</Dialog>}
    {setupOpen&&<Dialog label="Connect local Scout" className="modal setup-modal" onClose={()=>setSetupOpen(false)}>{close=><><div className="modal-head"><div><span>CONNECT THE RESEARCH CORE</span><h2>Run the real Scout.</h2></div><button onClick={close} aria-label="Close setup"><Icon name="close"/></button></div><p>The hosted site cannot run a local Python/Claude Code cycle. Start the bundled bridge on your own computer, or import a JSON export and HTML report. No wallet connection is needed.</p><div className="code-block"><span>TERMINAL 01</span><code>python3 bridge/server.py</code><span>TERMINAL 02</span><code>npm run dev</code><span>CREATE A SHAREABLE SNAPSHOT</span><code>python3 bridge/export.py --out scout-export.json</code></div><button className="button-primary" onClick={()=>{close();fileRef.current?.click();}}>Import existing export <Icon name="upload" size={16}/></button></>}</Dialog>}
  </>;
}
