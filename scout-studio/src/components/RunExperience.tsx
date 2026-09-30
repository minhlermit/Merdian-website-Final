import { useEffect, useState } from 'react';
import { Icon } from './Icons';

const phases = [
  ['DISCOVER', 'A stock-paired pool enters the watchlist.'],
  ['VERIFY', 'The Scout checks pool depth, ownership and claims.'],
  ['INVESTIGATE', 'A meaningful signal opens the research queue.'],
  ['SCORE', 'Fixed rules and the exit-risk floor hold the line.'],
  ['PRESENT', 'The evidence reaches a candidate board and memo.'],
];

export function RunExperience({onClose,onExplore}: {onClose:()=>void;onExplore:()=>void}) {
  const [step,setStep]=useState(0);
  useEffect(() => {
    if (step>=phases.length) return;
    const timer=setTimeout(()=>setStep(n=>n+1),750);
    return ()=>clearTimeout(timer);
  },[step]);
  return <div className="overlay modal-center" onMouseDown={e=>{if(e.target===e.currentTarget)onClose();}}>
    <div className="modal run-modal" role="dialog" aria-modal="true" aria-label="Guided Scout demo">
      <div className="modal-head"><div><span>GUIDED RUN / FICTIONAL SCENARIO</span><h2>{step===phases.length?'The trail is ready.':'Following the signal.'}</h2></div><button onClick={onClose} aria-label="Close guided run"><Icon name="close"/></button></div>
      <div className="run-stage"><div className="run-stage-art"><div className="run-stage-ring"/><img src="/assets/scout-mascot-pixel.png" alt="Pixel Scout mascot"/></div><div className="run-stages">{phases.map(([label,detail],i)=><div key={label} className={i<step?'done':i===step?'current':''}><span>{String(i+1).padStart(2,'0')}</span><div><b>{label}</b><p>{detail}</p></div><Icon name={i<step?'check':'arrow'} size={16}/></div>)}</div></div>
      <div className="run-end"><p>{step===phases.length?'Demo complete. The candidates are fictional; the real Python Scout runs through the local bridge.':'A simulated walkthrough of the bundled ZIP. No chain request, MC consumption or payment occurs.'}</p><button className="button-primary" onClick={onExplore}>{step===phases.length?'Explore candidates':'Skip to candidates'} <Icon name="arrowUp" size={17}/></button></div>
    </div>
  </div>;
}
