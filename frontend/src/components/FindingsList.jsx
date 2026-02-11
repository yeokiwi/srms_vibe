import React, { useState } from 'react';

const CONFIDENCE_STYLES = {
  CONFIRMED: 'bg-green-100 text-green-800 border-green-300',
  'LIKELY RECENT': 'bg-yellow-100 text-yellow-800 border-yellow-300',
};

const SENTIMENT_STYLES = {
  Positive: 'text-green-600',
  Neutral: 'text-gray-500',
  Negative: 'text-red-600',
};

const IMPORTANCE_STYLES = {
  High: 'bg-red-100 text-red-700',
  Medium: 'bg-blue-100 text-blue-700',
  Low: 'bg-gray-100 text-gray-600',
};

export default function FindingsList({ findings }) {
  if (!findings || findings.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">
        No findings match the current filters.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {findings.map((finding, i) => (
        <FindingCard key={i} finding={finding} index={i + 1} />
      ))}
    </div>
  );
}

function FindingCard({ finding, index }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 focus:outline-none"
      >
        <div className="flex items-start gap-3">
          {/* Number */}
          <span className="text-xs text-gray-400 font-mono mt-1 w-6 flex-shrink-0">
            #{index}
          </span>

          {/* Badges */}
          <div className="flex flex-wrap items-center gap-2 flex-1 min-w-0">
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded border ${
                CONFIDENCE_STYLES[finding.confidence] || 'bg-gray-100'
              }`}
            >
              {finding.confidence}
            </span>
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-gray-100 text-gray-700">
              {finding.category}
            </span>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded ${
                IMPORTANCE_STYLES[finding.importance] || ''
              }`}
            >
              {finding.importance}
            </span>

            {/* Title */}
            <h3 className="text-sm font-medium text-gray-900 truncate flex-1 min-w-0">
              {finding.title}
            </h3>
          </div>

          {/* Date */}
          <div className="text-xs text-gray-400 flex-shrink-0">
            {finding.date || 'No date'}
          </div>

          {/* Chevron */}
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${
              expanded ? 'rotate-180' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-3 ml-9">
          {/* Summary */}
          <p className="text-sm text-gray-700 mb-3">{finding.summary}</p>

          {/* Source URL */}
          <div className="mb-3">
            <span className="text-xs font-medium text-gray-500">Source: </span>
            <a
              href={finding.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline break-all"
            >
              {finding.source_url}
            </a>
          </div>

          {/* Evidence */}
          {finding.evidence && finding.evidence.length > 0 && (
            <div className="mb-3">
              <span className="text-xs font-medium text-gray-500 block mb-1">Evidence:</span>
              <ul className="space-y-0.5">
                {finding.evidence.map((e, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                    <span className="text-gray-400 mt-0.5">-</span>
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Excerpt */}
          {finding.excerpt && (
            <div className="bg-gray-50 rounded p-3">
              <span className="text-xs font-medium text-gray-500 block mb-1">Excerpt:</span>
              <p className="text-xs text-gray-600 italic">{finding.excerpt}</p>
            </div>
          )}

          {/* Sentiment */}
          <div className="mt-2 text-xs">
            <span className="text-gray-500">Sentiment: </span>
            <span className={SENTIMENT_STYLES[finding.sentiment] || ''}>
              {finding.sentiment}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
