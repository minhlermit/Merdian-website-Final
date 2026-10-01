import { relativeTime } from '../lib/format';
import type { ScoutPayload } from '../types';

const utcTime = (seconds: number) => `${new Date(seconds * 1000).toISOString().slice(11, 16)} UTC`;

/** Sits under the Run button: what the board shows, how fresh it is, and what Run and reset actually do. */
export function DataStatus({ data, bridge, running, clock }: { data: ScoutPayload; bridge: boolean; running: boolean; clock: string }) {
  const demo = data.source === 'demo';
  const viewing = demo ? 'Demo · fictional data' : data.source === 'local' ? 'Live · your local Scout' : 'Imported export';
  const updated = demo ? 'Not a research run' : `${relativeTime(data.generated)} · ${utcTime(data.generated)}`;
  const run = running
    ? 'Scout is running on this computer. New results appear here when the cycle finishes.'
    : bridge
      ? 'Run Scout starts a real research cycle on this computer. It can take several minutes when a signal needs investigation.'
      : 'Run demo plays a fictional walkthrough. The hosted site cannot run the research engine.';
  const reset = demo && !data.candidates.length
    ? 'The previous candidates were cleared at the last reset. Run the demo to bring the example set back.'
    : 'The board clears at the next reset. A reset never runs new research.';

  return <div className="data-status" role="note" aria-label="Data status">
    <dl>
      <div><dt>Viewing</dt><dd><span className={`status-pill ${demo ? 'is-demo' : 'is-live'}`} aria-hidden="true" />{viewing}</dd></div>
      <div><dt>Last updated</dt><dd>{updated}</dd></div>
      <div><dt>Next reset in</dt><dd><span className="tabular">{clock}</span> <small>UTC 00 · 06 · 12 · 18</small></dd></div>
    </dl>
    <p><b>Run:</b> {run} <b>Reset:</b> {reset}</p>
  </div>;
}
