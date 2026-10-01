export type EvidenceLevel = 'VERIFIED_ONCHAIN' | 'VERIFIED_OFFCHAIN' | 'LIKELY' | 'UNCONFIRMED' | 'CONFLICT';
export type ResearchStatus = 'COMPLETE' | 'INCOMPLETE' | 'FAILED' | 'QUEUED' | 'WATCH';
export type ExitRisk = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';

export interface Evidence {
  label: string;
  level: EvidenceLevel;
  url?: string;
  detail?: string;
}

export interface SignalEvent {
  id: string;
  type: string;
  token: string;
  symbol: string;
  time: number;
  severity: number;
  detail?: string;
}

export interface Candidate {
  address: string;
  symbol: string;
  name: string;
  pair: string;
  isOfficialPair: boolean | null;
  researchStatus: ResearchStatus;
  mode: string | null;
  verdict: string;
  conviction: string | null;
  growth: string | null;
  exitRisk: ExitRisk;
  liquidity: number | null;
  volume24: number | null;
  holders: number | null;
  top10: number | null;
  score: number | null;
  scoreMax: number | null;
  price: number | null;
  liquidityHistory: number[];
  updated: number | null;
  thesis: string;
  product: string;
  growthEngine: string;
  risks: string[];
  catalysts: string[];
  evidence: Evidence[];
  links: { site?: string; x?: string; explorer?: string };
}

export interface ScoutPayload {
  schema: 1;
  generated: number;
  source: 'local' | 'demo' | 'export';
  runId: string | null;
  reportAvailable: boolean;
  candidates: Candidate[];
  events: SignalEvent[];
  warnings: string[];
}
