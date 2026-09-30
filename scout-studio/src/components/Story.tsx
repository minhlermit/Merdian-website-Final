import { useEffect, useState } from 'react';
import { Icon } from './Icons';

const chapters = [
  {n:'01',tag:'THE SPARK',title:'A new pool appears.',body:'Every six hours, the Scout checks public market data for stock-paired tokens. It compares snapshots, so a meaningful change becomes a signal instead of another noisy listing.',code:'scout_cycle.py',output:'POOL → SNAPSHOT → EVENT',signal:'NEW STOCK-PAIRED POOL'},
  {n:'02',tag:'THE PROOF',title:'The pair gets checked.',body:'On-chain data and a claim ledger test the stock pair, pool depth, holders and contract permissions. A project’s story remains a claim until evidence supports it.',code:'onchain.py  +  ledger.py',output:'CLAIM → SOURCE → CONFIDENCE',signal:'VERIFIED ON-CHAIN'},
  {n:'03',tag:'THE INVESTIGATION',title:'Only signals use AI.',body:'If nothing important changed, the cycle stops. When there is a signal, specialized research investigates the creator, product, incentives and risks without rereading unchanged evidence.',code:'context.py  →  research agents',output:'SIGNAL → RESEARCH QUEUE',signal:'EVIDENCE PACKET READY'},
  {n:'04',tag:'THE BOUNDARY',title:'The rules hold the line.',body:'A fixed scorecard and exit-risk floor come from the Python core. The writer cannot improve a rating with persuasive prose. The final memo runs only after research is marked complete.',code:'run_report.py  /  COMPLETE GATE',output:'SCORE → RISK FLOOR → GATE',signal:'RESEARCH COMPLETE'},
  {n:'05',tag:'THE DELIVERABLE',title:'One report. Clear reasons.',body:'A comparison board and investor memos land in one HTML report. You can inspect what supports each conclusion, what remains unverified and what could change the thesis.',code:'latest.html',output:'CANDIDATES → INVESTOR MEMO',signal:'READY TO EXPLORE'},
];

export function Story({onRun,onConsole,live}: {onRun:()=>void;onConsole:()=>void;live:boolean}) {
  const [active,setActive] = useState(0);
  useEffect(() => {
    const elements=document.querySelectorAll<HTMLElement>('.story-chapter');
    const observer=new IntersectionObserver(entries=>{
      const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];
      if(visible)setActive(Number((visible.target as HTMLElement).dataset.step||0));
    },{threshold:[.25,.5,.75],rootMargin:'-10% 0px -28% 0px'});
    elements.forEach(el=>observer.observe(el));return()=>observer.disconnect();
  },[]);
  const step=chapters[active];
  return <section className="story-section" id="story">
    <div className="wrap-wide"><div className="story-intro" data-reveal><div className="kicker"><span>01 / UNDER THE HOOD</span><span className="kicker-rule"/></div><div className="story-intro-grid"><h2>Before the verdict,<br/><em>follow the trail.</em></h2><p>The ZIP is a research engine, not a trading bot. Here is what happens between a new token appearing and a memo you can actually inspect.</p></div></div>
    <div className="story-layout"><div className="story-steps">{chapters.map((item,i)=><article key={item.n} className={`story-chapter ${i===active?'active':''}`} data-step={i} data-reveal><span className="story-chapter-num">{item.n} / 05 <i/></span><small>{item.tag}</small><h3>{item.title}</h3><p>{item.body}</p><button onClick={()=>{setActive(i);document.querySelectorAll('.story-chapter')[i]?.scrollIntoView({behavior:'smooth',block:'center'});}} aria-label={`Show chapter ${item.n}`}>Explore this step <Icon name="arrow" size={15}/></button></article>)}</div>
    <div className="story-visual-wrap"><div className="story-visual" aria-live="polite"><div className="story-visual-head"><span className="signal-light"/> SCOUT / FIELD NOTES <span>0{active+1} OF 05</span></div><div className="story-scan"><div className={`story-orbit story-orbit-${active}`}><img src="/assets/signal-orbit-3d.png" alt=""/></div><div className="scan-lines"/></div><div className="story-visual-info" key={active}><span>{step.tag} <b>◆</b> {step.signal}</span><strong>{step.output}</strong><code>$ {step.code}</code></div><div className="story-progress">{chapters.map((x,i)=><button key={x.n} className={i===active?'active':''} onClick={()=>{setActive(i);document.querySelectorAll('.story-chapter')[i]?.scrollIntoView({behavior:'smooth',block:'center'});}} aria-label={`Go to story step ${i+1}`}><i/></button>)}</div></div></div></div>
    <div className="story-finale" data-reveal><div><span>NOW YOU KNOW WHAT RUN MEANS</span><h3>Curiosity is good.<br/>Evidence is better.</h3><p>{live?'Start a real Scout cycle on this machine.':'Try the guided demo first, then inspect the candidate board. This preview does not call live chain APIs.'}</p></div><div className="finale-actions"><button className="button-primary" onClick={onRun}>{live?'Run Scout now':'Run the demo'} <Icon name="arrowUp" size={19}/></button><button className="button-outline" onClick={onConsole}>View candidates <Icon name="arrow" size={18}/></button></div></div></div>
  </section>;
}
