const API_BASE = '/api';

export async function startAnalysis({ url, sections, days }) {
  const resp = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, sections, days }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function getAnalysis(taskId) {
  const resp = await fetch(`${API_BASE}/analyze/${taskId}`);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export function getExportUrl(taskId, format) {
  return `${API_BASE}/analyze/${taskId}/export/${format}`;
}
