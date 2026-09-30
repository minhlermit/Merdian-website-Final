import type { SVGProps } from 'react';

type Name = 'arrow' | 'arrowUp' | 'search' | 'spark' | 'layers' | 'grid' | 'close' | 'download' | 'upload' | 'play' | 'check' | 'copy' | 'external' | 'shield' | 'menu' | 'chevron' | 'file' | 'refresh' | 'info' | 'filter' | 'wallet' | 'lock';
const paths: Record<Name, React.ReactNode> = {
  arrow: <><path d="M4 12h16"/><path d="m14 6 6 6-6 6"/></>,
  arrowUp: <><path d="M5 19 19 5"/><path d="M8 5h11v11"/></>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></>,
  spark: <><path d="m12 2 1.9 6.1L20 10l-6.1 1.9L12 18l-1.9-6.1L4 10l6.1-1.9L12 2Z"/><path d="m19 18 .8 2.2L22 21l-2.2.8L19 24l-.8-2.2L16 21l2.2-.8L19 18Z"/></>,
  layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
  grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
  close: <><path d="M5 5 19 19M19 5 5 19"/></>,
  download: <><path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/></>,
  upload: <><path d="M12 17V5m-5 5 5-5 5 5M4 17v4h16v-4"/></>,
  play: <path d="m7 4 13 8-13 8V4Z"/>,
  check: <path d="m4 12 5 5L20 6"/>,
  copy: <><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></>,
  external: <><path d="M13 5h6v6M19 5l-9 9"/><path d="M19 13v6H5V5h6"/></>,
  shield: <><path d="m12 2 8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4Z"/><path d="m8 12 3 3 5-5"/></>,
  menu: <><path d="M3 6h18M3 12h18M3 18h18"/></>,
  chevron: <path d="m7 10 5 5 5-5"/>,
  file: <><path d="M5 2h10l4 4v16H5V2Z"/><path d="M15 2v5h4M8 12h8M8 16h8"/></>,
  refresh: <><path d="M20 11a8 8 0 0 0-14-5L3 9m0-6v6h6M4 13a8 8 0 0 0 14 5l3-3m0 6v-6h-6"/></>,
  info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/></>,
  filter: <><path d="M3 5h18M6 12h12M10 19h4"/></>,
  wallet: <><rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 9V5a2 2 0 0 1 2-2h13M15 12h6v5h-6a2.5 2.5 0 0 1 0-5Z"/><path d="M16 14.5h.01"/></>,
  lock: <><rect x="4" y="10" width="16" height="12" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 15v3"/></>,
};

export function Icon({name, size = 20, ...props}: SVGProps<SVGSVGElement> & {name: Name; size?: number}) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg>;
}
