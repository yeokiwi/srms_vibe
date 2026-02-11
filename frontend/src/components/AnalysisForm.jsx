import React, { useState } from 'react';

export default function AnalysisForm({ onSubmit, loading }) {
  const [url, setUrl] = useState('');
  const [sections, setSections] = useState('');
  const [days, setDays] = useState(30);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    onSubmit({
      url: url.trim(),
      sections: sections
        .split(',')
        .map(s => s.trim())
        .filter(Boolean),
      days,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="space-y-4">
        {/* URL Input */}
        <div>
          <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
            Website URL
          </label>
          <input
            id="url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            required
            className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          <p className="text-xs text-gray-400 mt-1">
            Enter the website you want to analyze for recent changes
          </p>
        </div>

        {/* Advanced Options Toggle */}
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          {showAdvanced ? 'Hide' : 'Show'} advanced options
        </button>

        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
            {/* Sections */}
            <div>
              <label htmlFor="sections" className="block text-sm font-medium text-gray-700 mb-1">
                Specific Sections (optional)
              </label>
              <input
                id="sections"
                type="text"
                value={sections}
                onChange={(e) => setSections(e.target.value)}
                placeholder="/blog, /news, /pricing"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
              <p className="text-xs text-gray-400 mt-1">Comma-separated paths</p>
            </div>

            {/* Date Range */}
            <div>
              <label htmlFor="days" className="block text-sm font-medium text-gray-700 mb-1">
                Look Back Period
              </label>
              <div className="flex items-center gap-3">
                <input
                  id="days"
                  type="range"
                  min="7"
                  max="90"
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm font-medium text-gray-700 w-20 text-right">
                  {days} days
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="w-full bg-blue-600 text-white rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Analyzing...' : 'Analyze Website'}
        </button>
      </div>
    </form>
  );
}
