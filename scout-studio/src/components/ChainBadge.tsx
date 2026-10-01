import { useState } from 'react';
import { Icon } from './Icons';

// Drop the official Robinhood Chain mark at this path (SVG, square) to show it in the badge.
// Until the file exists the badge falls back to a neutral link glyph, never a lookalike logo.
export const CHAIN_LOGO_SRC = '/assets/brand/robinhood-chain.svg';

export function ChainBadge({ className = '' }: { className?: string }) {
  const [logo, setLogo] = useState<'pending' | 'ok' | 'missing'>('pending');
  return <p className={`chain-badge ${className}`}>
    <span className="chain-badge-logo" aria-hidden="true">
      {logo !== 'missing' && <img src={CHAIN_LOGO_SRC} alt="" width={22} height={22} hidden={logo !== 'ok'} onLoad={() => setLogo('ok')} onError={() => setLogo('missing')} />}
      {logo !== 'ok' && <Icon name="link" size={14} />}
    </span>
    <span>Independent research on <b>Robinhood Chain</b></span>
  </p>;
}
