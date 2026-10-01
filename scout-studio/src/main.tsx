import React, { lazy, Suspense } from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const AssetLab = lazy(() => import('./lab/AssetLab'));
const isLab = window.location.pathname.replace(/\/+$/, '') === '/lab';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {isLab ? <Suspense fallback={<p className="lab-loading">Loading asset lab…</p>}><AssetLab /></Suspense> : <App />}
  </React.StrictMode>,
);
