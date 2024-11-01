// frontend/components/ResultViewer/index.jsx
import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import JsonView from './JsonView';
import HumanReadable from './HumanReadable';
import DownloadButton from './DownloadButton';
import OriginalView from './OriginalView';

/**
 * ResultViewer component displays the parsed results in different formats.
 */
const ResultViewer = () => {
  const parsingResult = useSelector((state) => state.parsing.parsingResult);
  const [view, setView] = useState('human'); // 'human', 'json', 'original'

  if (!parsingResult) return null;

  return (
    <div className="mt-6 bg-white p-6 rounded shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Parsed Results</h2>
        <div className="flex items-center">
          {['human', 'json', 'original'].map((type) => (
            <button
              key={type}
              onClick={() => setView(type)}
              className={`mr-2 px-3 py-1 rounded transition-colors duration-200 ${
                view === type ? 'bg-blue-500 text-white' : 'bg-gray-200 hover:bg-gray-300'
              }`}
              aria-pressed={view === type}
              aria-label={`View parsed results as ${type}`}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4">
        {view === 'human' && (
          <React.Suspense fallback={<p>Loading Human Readable View...</p>}>
            <HumanReadable data={parsingResult} />
          </React.Suspense>
        )}
        {view === 'json' && (
          <React.Suspense fallback={<p>Loading JSON View...</p>}>
            <JsonView data={parsingResult} />
          </React.Suspense>
        )}
        {view === 'original' && (
          <React.Suspense fallback={<p>Loading Original View...</p>}>
            <OriginalView data={parsingResult} />
          </React.Suspense>
        )}
      </div>

      <DownloadButton data={parsingResult} />
    </div>
  );
};

export default ResultViewer;
