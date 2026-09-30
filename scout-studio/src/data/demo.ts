import type { Candidate, ScoutPayload } from '../types';

const now = Date.now() / 1000;
const base: Omit<Candidate, 'address' | 'symbol' | 'name' | 'pair' | 'verdict' | 'exitRisk' | 'liquidity' | 'volume24' | 'holders' | 'top10' | 'score' | 'price' | 'liquidityHistory' | 'thesis' | 'product' | 'growthEngine' | 'risks' | 'catalysts' | 'evidence' | 'updated'> = {
  isOfficialPair: true, researchStatus: 'COMPLETE', mode: 'DEEP', conviction: 'MONITOR', growth: 'UNKNOWN', scoreMax: 30, links: {},
};

const candidates: Candidate[] = [
  { ...base, address: 'demo-01', symbol: 'AURA', name: 'Aura Protocol · fictional', pair: 'NVDA', verdict: 'RESEARCH', exitRisk: 'MEDIUM', liquidity: 318400, volume24: 84400, holders: 1682, top10: 29.4, score: 21, price: 0.0124, liquidityHistory: [110,130,128,148,186,202,191,218,240,237,260,275,318], updated: now - 1320,
    thesis: 'A simulated example of a stock-paired community token with a proposed creator tool.', product: 'Prototype creator dashboard; independent usage has not been verified.', growthEngine: 'Attention around a stock pair may bring traders; durable product demand is still unproven.', risks: ['Product activity is unverified', 'Stock pairing does not mean stock ownership', 'Liquidity can move quickly'], catalysts: ['Verify active users and product releases', 'Confirm creator statements through official sources'], evidence: [{label:'Pool and pair observed in simulated on-chain data',level:'VERIFIED_ONCHAIN'}, {label:'Creator adoption claim awaits independent confirmation',level:'UNCONFIRMED'}] },
  { ...base, address: 'demo-02', symbol: 'LUMA', name: 'Luma Network · fictional', pair: 'TSLA', verdict: 'WATCH', exitRisk: 'HIGH', liquidity: 71200, volume24: 48600, holders: 812, top10: 48.1, score: 15, price: 0.0081, liquidityHistory: [130,120,108,96,90,101,86,84,82,76,74,71], updated: now - 2920,
    thesis: 'A simulated narrative token with early social attention and limited market depth.', product: 'No independently verified product in this sample.', growthEngine: 'Social attention drives current activity; repeat usage has not been demonstrated.', risks: ['Shallow liquidity', 'High holder concentration', 'No verified product'], catalysts: ['Improved pool depth', 'Independent product evidence'], evidence: [{label:'Simulated pool depth and holder concentration',level:'VERIFIED_ONCHAIN'}, {label:'Team identity is not confirmed',level:'UNCONFIRMED'}] },
  { ...base, address: 'demo-03', symbol: 'FRAME', name: 'Frame Labs · fictional', pair: 'COIN', verdict: 'RESEARCH', exitRisk: 'MEDIUM', liquidity: 204700, volume24: 31900, holders: 1240, top10: 24.6, score: 19, price: 0.0039, liquidityHistory: [90,96,103,99,125,144,159,176,169,182,198,192,204], updated: now - 6200,
    thesis: 'A simulated token with a proposed research utility and a stock-token pair.', product: 'Research tooling concept shown for interface demonstration.', growthEngine: 'Potential usage depends on the research tool gaining repeat users.', risks: ['No validated revenue', 'Token value capture uncertain'], catalysts: ['Public usage metrics', 'Verified token utility'], evidence: [{label:'Pair shown in simulated market snapshot',level:'VERIFIED_ONCHAIN'}, {label:'Research utility is a simulated claim',level:'UNCONFIRMED'}] },
  { ...base, address: 'demo-04', symbol: 'ECHO', name: 'Echo Markets · fictional', pair: 'SPY', verdict: 'CAUTION', exitRisk: 'CRITICAL', liquidity: 13400, volume24: 127000, holders: 430, top10: 62.2, score: 8, price: 0.0006, liquidityHistory: [105,92,81,70,60,56,48,42,35,29,20,16,13], updated: now - 510,
    thesis: 'A simulated warning case where turnover is high relative to exit liquidity.', product: 'No verified product.', growthEngine: 'No durable economic loop demonstrated.', risks: ['Very thin exit liquidity', 'Concentrated holders', 'Possible simulated liquidity collapse'], catalysts: ['Explain liquidity movement', 'Verify contract permissions'], evidence: [{label:'Simulated liquidity collapse signal',level:'VERIFIED_ONCHAIN'}, {label:'Reason for the movement is unknown',level:'UNCONFIRMED'}] },
];

export const demo: ScoutPayload = {
  schema: 1, generated: now, source: 'demo', runId: null, reportAvailable: false, candidates,
  events: [
    {id:'e1',type:'LIQUIDITY_COLLAPSE',token:'demo-04',symbol:'ECHO',time:now-510,severity:4,detail:'Liquidity fell sharply in this fictional scenario; cause not established.'},
    {id:'e2',type:'VOLUME_ACCELERATION',token:'demo-01',symbol:'AURA',time:now-1320,severity:2,detail:'24h volume rose relative to the previous snapshot.'},
    {id:'e3',type:'PARTICIPANT_SURGE',token:'demo-03',symbol:'FRAME',time:now-6200,severity:2,detail:'Unique market participants increased in this fictional scenario.'},
  ], warnings:['All names, addresses and metrics shown in demo mode are fictional.'],
};
