export function money(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return '—';
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}m`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(value >= 100_000 ? 0 : 1)}k`;
  return `$${value.toLocaleString('en-US', {maximumFractionDigits: 0})}`;
}

export function compact(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? '—' : value.toLocaleString('en-US');
}

export function relativeTime(time: number | null | undefined): string {
  if (!time) return 'Unknown';
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - time));
  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function shortAddress(address: string): string {
  return address.startsWith('0x') ? `${address.slice(0, 6)}…${address.slice(-4)}` : 'DEMO ID';
}

export function safeLink(url?: string): string | undefined {
  if (!url) return undefined;
  try {
    const parsed = new URL(url);
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : undefined;
  } catch { return undefined; }
}
