import React, { useState } from 'react';
import { getExportUrl } from '../api.js';

export default function ExportBar({ taskId }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      const resp = await fetch(getExportUrl(taskId, 'json'));
      const text = await resp.text();
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: open in new tab
      window.open(getExportUrl(taskId, 'json'), '_blank');
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm font-medium text-gray-700">Export:</span>

      <a
        href={getExportUrl(taskId, 'json')}
        download
        className="inline-flex items-center gap-1 px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 transition-colors"
      >
        JSON
      </a>

      <a
        href={getExportUrl(taskId, 'csv')}
        download
        className="inline-flex items-center gap-1 px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 transition-colors"
      >
        CSV
      </a>

      <a
        href={getExportUrl(taskId, 'pdf')}
        download
        className="inline-flex items-center gap-1 px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 transition-colors"
      >
        PDF
      </a>

      <button
        onClick={handleCopy}
        className="inline-flex items-center gap-1 px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 transition-colors"
      >
        {copied ? 'Copied!' : 'Copy JSON'}
      </button>
    </div>
  );
}
