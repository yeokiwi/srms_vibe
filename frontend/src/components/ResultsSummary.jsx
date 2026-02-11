import React from 'react';

export default function ResultsSummary({ summary }) {
  if (!summary) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Analysis Summary</h2>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Findings" value={summary.total_findings} color="blue" />
        <StatCard label="Confirmed" value={summary.confirmed_count} color="green" />
        <StatCard label="Likely Recent" value={summary.likely_recent_count} color="yellow" />
        <StatCard
          label="Categories"
          value={Object.keys(summary.category_breakdown || {}).length}
          color="purple"
        />
      </div>

      {/* Category Breakdown */}
      {summary.category_breakdown && Object.keys(summary.category_breakdown).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">By Category</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(summary.category_breakdown).map(([cat, count]) => (
              <span
                key={cat}
                className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-700"
              >
                {cat}
                <span className="font-semibold">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Timeline */}
      {summary.timeline && summary.timeline.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Timeline</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {summary.timeline.map((item, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span className="text-gray-400 font-mono w-24 flex-shrink-0">
                  {item.date}
                </span>
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    item.confidence === 'CONFIRMED' ? 'bg-green-500' : 'bg-yellow-500'
                  }`}
                />
                <span className="text-gray-700 truncate">{item.title}</span>
                <span className="text-gray-400 text-xs flex-shrink-0">{item.category}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  };

  return (
    <div className={`rounded-lg border p-4 ${colors[color] || colors.blue}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs font-medium opacity-75">{label}</div>
    </div>
  );
}
