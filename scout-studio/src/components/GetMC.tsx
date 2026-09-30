import { Icon } from './Icons';
import { Dialog } from './Dialog';

const plans=[
  {name:'Explorer',kind:'START HERE',mc:'0',cadence:'free preview',lines:['Follow the six-hour research board','Read public evidence and risk flags','Explore the guided demo'],featured:false},
  {name:'Researcher',kind:'PREMIUM CONCEPT',mc:'300',cadence:'MC each month',lines:['MC available after subscription clears','Run deeper research on chosen tokens','Keep memo and evidence history'],featured:true},
  {name:'Studio',kind:'TEAM CONCEPT',mc:'1,200',cadence:'MC each month',lines:['Shared research allocation','Priority batch investigations','Export and collaboration workspace'],featured:false},
];

export function GetMC({onClose,onWallet,onExplore,connected}: {onClose:()=>void;onWallet:()=>void;onExplore:()=>void;connected:boolean}) {
  return <Dialog label="Get MC and subscriptions" className="modal mc-modal" onClose={onClose}>{close => <><div className="modal-head"><div><span>MC / RESEARCH UTILITY CONCEPT</span><h2>Research has a cost.<br/><em>Make it visible.</em></h2></div><button onClick={close} aria-label="Close Get MC"><Icon name="close"/></button></div>
    <p className="mc-intro">MC is the proposed usage token for on-demand research. These packages are product ideas, with no price or token sale enabled yet. The public six-hour board stays readable without MC.</p>
    <div className="mc-flow"><div><span>01</span><b>Subscribe or top up</b><small>Premium grants MC after payment settles. Top-ups need a separate wallet confirmation.</small></div><Icon name="arrow" size={18}/><div><span>02</span><b>Quote a research job</b><small>Show the MC cost before a user confirms.</small></div><Icon name="arrow" size={18}/><div><span>03</span><b>Complete, then burn</b><small>Burn the quoted MC only after a verified successful job.</small></div></div>
    <div className="plans-grid">{plans.map(plan=><div className={`plan-card ${plan.featured?'featured':''}`} key={plan.name}><span>{plan.kind}</span><h3>{plan.name}</h3><div className="plan-amount"><strong>{plan.mc}</strong><div><b>MC</b><small>{plan.cadence}</small></div></div><ul>{plan.lines.map(line=><li key={line}><Icon name="check" size={14}/>{line}</li>)}</ul><button onClick={plan.name==='Explorer'?onExplore:connected?close:()=>{close();onWallet();}}>{plan.name==='Explorer'?'Explore the board':connected?'Connected · preview only':'Connect wallet'} <Icon name="arrowUp" size={16}/></button></div>)}</div>
    <div className="mc-usage"><div><span>ILLUSTRATIVE JOB QUOTES</span><h3>Every command gets a price first.</h3></div><div><span>Targeted scan <b>4 MC</b></span><span>Deep investigation <b>18 MC</b></span><span>Full investor memo <b>30 MC</b></span></div></div>
    <p className="mc-disclosure">Concept values for UX review. No MC balance, subscription charge, token mint, approval or burn is active. A real launch needs a deployed contract, billing and entitlements, secure job verification, wallet spend confirmation and published terms.</p>
  </>}</Dialog>;
}
