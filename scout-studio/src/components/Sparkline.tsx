export function Sparkline({values, risk = false, id}: {values:number[];risk?:boolean;id:string}) {
  const list = values.length > 1 ? values : [0,0];
  const min = Math.min(...list), max = Math.max(...list);
  const range = max - min || 1;
  const pts = list.map((v,i) => `${i/(list.length-1)*160},${45-(v-min)/range*37}`).join(' ');
  const area = `0,50 ${pts} 160,50`;
  const color = risk ? '#ec866d' : '#e7b667';
  return <svg viewBox="0 0 160 54" preserveAspectRatio="none" className="sparkline" role="img" aria-label="Liquidity history trend">
    <defs><linearGradient id={`fill-${id}`} x1="0" y1="0" x2="0" y2="1"><stop stopColor={color} stopOpacity=".3"/><stop offset="1" stopColor={color} stopOpacity="0"/></linearGradient></defs>
    <polygon points={area} fill={`url(#fill-${id})`}/><polyline points={pts} fill="none" stroke={color} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke"/>
  </svg>;
}
