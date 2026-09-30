import { useState } from 'react';
import type { Candidate, EvidenceLevel } from '../types';
import { compact, money, relativeTime, safeLink, shortAddress } from '../lib/format';
import { Icon } from './Icons';
import { Sparkline } from './Sparkline';
import { Dialog } from './Dialog';

const evidenceNames: Record<EvidenceLevel,string> = {VERIFIED_ONCHAIN:'ON-CHAIN VERIFIED',VERIFIED_OFFCHAIN:'OFF-CHAIN VERIFIED',LIKELY:'LIKELY',UNCONFIRMED:'UNCONFIRMED',CONFLICT:'CONFLICT'};

export function DetailPanel({candidate:c, onClose, onReport, hasReport}: {candidate:Candidate;onClose:()=>void;onReport:()=>void;hasReport:boolean}) {
  const [copied,setCopied] = useState(false);
  const explorer = safeLink(c.links.explorer);
  const copy = async () => { try { await navigator.clipboard.writeText(c.address); setCopied(true); setTimeout(()=>setCopied(false),1800); } catch { /* clipboard unavailable */ } };
  return <Dialog label={`${c.symbol} research`} className="detail-panel" variant="drawer" onClose={onClose}>{close => <>
    <div className="panel-head"><span>RESEARCH FILE <b>/{c.symbol}</b></span><button onClick={close} aria-label="Close research"><Icon name="close" size={22}/></button></div>
    <div className="panel-scroll"><div className="panel-identity"><div className="panel-icon">{c.symbol.slice(0,1)}</div><div><span>ROBINHOOD CHAIN / {c.pair} PAIR</span><h2>{c.symbol}<small>{c.name}</small></h2></div></div>
    <div className="panel-status"><span className={`risk-tag risk-${c.exitRisk.toLowerCase()}`}><i/>{c.exitRisk} EXIT RISK</span><span>{c.verdict.replace(/_/g,' ')} {c.scoreMax ? `· ${c.score}/${c.scoreMax}` : ''}</span><span>{c.researchStatus} {c.mode ? `· ${c.mode}`:''}</span></div>
    <div className="panel-chart"><Sparkline values={c.liquidityHistory} risk={c.exitRisk==='HIGH'||c.exitRisk==='CRITICAL'} id={`panel-${c.address.replace(/[^a-z0-9]/gi,'')}`}/><span>RECENT LIQUIDITY SNAPSHOTS</span></div>
    <div className="panel-stats"><div><small>POOL LIQUIDITY</small><strong>{money(c.liquidity)}</strong></div><div><small>24H VOLUME</small><strong>{money(c.volume24)}</strong></div><div><small>HOLDERS</small><strong>{compact(c.holders)}</strong></div><div><small>TOP 10 EOA</small><strong>{c.top10 == null?'—':`${c.top10}%`}</strong></div></div>
    <section className="panel-section"><div className="section-label"><span>01</span> THE THESIS</div><p className="thesis">{c.thesis || 'A research memo has not been completed for this token.'}</p><div className="mini-grid"><div><small>PRODUCT</small><p>{c.product || 'Not yet verified.'}</p></div><div><small>GROWTH ENGINE</small><p>{c.growthEngine || 'No established thesis.'}</p></div></div></section>
    <section className="panel-section"><div className="section-label"><span>02</span> WHAT TO CHECK</div><div className="check-columns"><div><h3>Risk flags</h3>{c.risks.length?<ul>{c.risks.map((r,i)=><li key={i}><span className="list-orange">↗</span>{r}</li>)}</ul>:<p className="muted">No written risk synthesis yet.</p>}</div><div><h3>Next catalysts</h3>{c.catalysts.length?<ul>{c.catalysts.map((x,i)=><li key={i}><span>↗</span>{x}</li>)}</ul>:<p className="muted">No catalysts recorded.</p>}</div></div></section>
    <section className="panel-section"><div className="section-label"><span>03</span> EVIDENCE LEDGER</div><div className="evidence-list">{c.evidence.length?c.evidence.map((e,i)=><div className="evidence-item" key={i}><span className={`evidence-dot ev-${e.level.toLowerCase()}`}/><div><b>{e.label}</b>{e.detail&&<p>{e.detail}</p>}<small>{evidenceNames[e.level] ?? e.level}</small></div>{safeLink(e.url)&&<a href={safeLink(e.url)} target="_blank" rel="noopener noreferrer" aria-label="Open evidence source"><Icon name="external" size={16}/></a>}</div>):<p className="muted">No supporting evidence recorded yet. Treat the thesis as unverified.</p>}</div></section>
    <div className="panel-foot"><div><small>CONTRACT</small><button onClick={copy}>{shortAddress(c.address)} <Icon name={copied?'check':'copy'} size={14}/></button></div><div><small>UPDATED</small><span>{relativeTime(c.updated)}</span></div></div>
    <div className="panel-actions">{hasReport&&<button className="button-primary" onClick={onReport}>Read full investor report <Icon name="arrowUp" size={18}/></button>}{explorer&&<a href={explorer} target="_blank" rel="noopener noreferrer" className="button-outline">Explorer <Icon name="external" size={16}/></a>}</div>
    <p className="panel-disclaimer">Research only. Stock-paired tokens do not automatically convey stock ownership. Verify every claim before relying on it.</p></div>
  </>}</Dialog>;
}
