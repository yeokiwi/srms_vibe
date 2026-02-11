import React, { useState, useCallback } from 'react';
import AnalysisForm from './components/AnalysisForm.jsx';
import ProgressBar from './components/ProgressBar.jsx';
import ResultsSummary from './components/ResultsSummary.jsx';
import FindingsList from './components/FindingsList.jsx';
import ExportBar from './components/ExportBar.jsx';
import { startAnalysis, getAnalysis } from './api.js';

const POLL_INTERVAL = 1500;

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');

  // Filters
  const [confidenceFilter, setConfidenceFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [sortBy, setSortBy] = useState('default');

  const handleSubmit = useCallback(async (formData) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setProgress(0);
    setProgressMessage('Starting analysis...');

    try {
      const task = await startAnalysis(formData);
      const taskId = task.task_id;

      // Poll for results
      const poll = async () => {
        try {
          const status = await getAnalysis(taskId);
          setProgress(status.progress || 0);
          setProgressMessage(status.progress_message || '');

          if (status.status === 'complete') {
            setResult(status);
            setLoading(false);
          } else if (status.status === 'error') {
            setError(status.errors?.join(', ') || 'Analysis failed');
            setLoading(false);
          } else {
            setTimeout(poll, POLL_INTERVAL);
          }
        } catch (err) {
          setError(err.message);
          setLoading(false);
        }
      };

      setTimeout(poll, POLL_INTERVAL);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }, []);

  // Apply filters and sorting
  const filteredFindings = React.useMemo(() => {
    if (!result?.findings) return [];
    let items = [...result.findings];

    if (confidenceFilter !== 'all') {
      items = items.filter(f => f.confidence === confidenceFilter);
    }
    if (categoryFilter !== 'all') {
      items = items.filter(f => f.category === categoryFilter);
    }
    if (sortBy === 'date') {
      items.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
    } else if (sortBy === 'importance') {
      const order = { High: 0, Medium: 1, Low: 2 };
      items.sort((a, b) => (order[a.importance] ?? 2) - (order[b.importance] ?? 2));
    }

    return items;
  }, [result, confidenceFilter, categoryFilter, sortBy]);

  // Gather unique categories for filter
  const categories = React.useMemo(() => {
    if (!result?.findings) return [];
    return [...new Set(result.findings.map(f => f.category))];
  }, [result]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-gray-900">
            Website Change Analyzer
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Detect recent changes, updates, and announcements on any website.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-8">
        {/* Input Form */}
        <AnalysisForm onSubmit={handleSubmit} loading={loading} />

        {/* Progress */}
        {loading && (
          <ProgressBar progress={progress} message={progressMessage} />
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            <p className="font-medium">Analysis Error</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && result.status === 'complete' && (
          <>
            {/* Export Bar */}
            <ExportBar taskId={result.task_id} />

            {/* Summary */}
            <ResultsSummary summary={result.summary} />

            {/* Filters */}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex flex-wrap gap-4 items-center">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Confidence</label>
                  <select
                    value={confidenceFilter}
                    onChange={(e) => setConfidenceFilter(e.target.value)}
                    className="border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white"
                  >
                    <option value="all">All</option>
                    <option value="CONFIRMED">Confirmed</option>
                    <option value="LIKELY RECENT">Likely Recent</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Category</label>
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white"
                  >
                    <option value="all">All</option>
                    {categories.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Sort By</label>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white"
                  >
                    <option value="default">Default</option>
                    <option value="date">Date (newest first)</option>
                    <option value="importance">Importance</option>
                  </select>
                </div>
                <div className="ml-auto text-sm text-gray-500">
                  Showing {filteredFindings.length} of {result.findings.length} findings
                </div>
              </div>
            </div>

            {/* Findings */}
            <FindingsList findings={filteredFindings} />
          </>
        )}

        {/* Disclaimer */}
        <footer className="text-center text-xs text-gray-400 py-8">
          <p>
            This tool crawls publicly available pages and uses heuristics to detect recent changes.
            Results may not be 100% accurate. Always verify important findings manually.
          </p>
          <p className="mt-1">
            Respects robots.txt &middot; Rate-limited requests &middot; No data stored permanently
          </p>
        </footer>
      </main>
    </div>
  );
}
