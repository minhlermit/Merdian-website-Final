import type { Candidate } from '../types';
import { money, compact } from '../lib/format';
import { Icon } from './Icons';
import { Sparkline } from './Sparkline';

export function CandidateCard({candidate:c, onOpen, selected, onSelect}: {candidate:Candidate;onOpen:()=>void;selected:boolean;onSelect:()=>void}) {
  const risky = c.exitRisk === 'HIGH' || c.exitRisk === 'CRITICAL';
  const rating = ({RESEARCH_DEEPER:'RESEARCH DEEPER',UNPROVEN:'IDEA / UNPROVEN',SPECULATIVE:'SPECULATIVE',AVOID:'AVOID',UNRATED:'UNRATED',RESEARCH:'RESEARCH',WATCH:'WATCH',CAUTION:'CAUTION'} as Record<string,string>)[c.verdict] || c.verdict.replace(/_/g,' ');
  return <article className="candidate-card">
    <div className="card-top"><div className={`token-ident token-${c.symbol.length%4}`} aria-hidden="true">{c.symbol.slice(0,1)}</div><div className="card-title"><span>{c.symbol}</span><small>{c.name}</small></div><button className={`compare-toggle ${selected?'active':''}`} onClick={onSelect} aria-label={`${selected?'Remove':'Add'} ${c.symbol} ${selected?'from':'to'} comparison`} title="Compare">{selected?<Icon name="check" size={15}/>:<span>+</span>}</button></div>
    <div className="card-pair"><span className="tiny-diamond">◇</span> {c.symbol} / {c.pair} <span className="pair-note">{c.isOfficialPair === true ? 'OFFICIAL STOCK PAIR' : c.isOfficialPair === false ? 'UNVERIFIED PAIR' : 'PAIR PENDING'}</span></div>
    <div className="card-rating"><span>{rating}</span><span>{c.scoreMax ? `${c.score ?? 0} / ${c.scoreMax}` : 'NOT SCORED'}</span></div>
    <div className="card-chart"><Sparkline values={c.liquidityHistory} risk={risky} id={c.address.replace(/[^a-z0-9]/gi,'')}/><span>LIQUIDITY TREND</span></div>
    <div className="card-metrics"><div><small>POOL LIQUIDITY</small><strong>{money(c.liquidity)}</strong></div><div><small>24H VOLUME</small><strong>{money(c.volume24)}</strong></div><div><small>HOLDERS</small><strong>{compact(c.holders)}</strong></div></div>
    <div className="card-bottom"><span className={`risk-tag risk-${c.exitRisk.toLowerCase()}`}><i/>{c.exitRisk} EXIT RISK</span><button onClick={onOpen}>Open research <Icon name="arrowUp" size={16}/></button></div>
  </article>;
}
