// frontend/components/ResultViewer/index.jsx
import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import JsonView from './JsonView';
import HumanReadable from './HumanReadable';
import DownloadButton from './DownloadButton';

/**
 * ResultViewer component displays the parsed results in different formats.
 */
const ResultViewer = () => {
  const parsingResult = useSelector((state) => state.parsing.parsingResult);
  const [view, setView] = useState('human'); // 'human' or 'json'

  // If there's no parsing result, return null to avoid rendering anything
  if (!parsingResult) return null;

  // Button list to avoid redundancy
  const views = [
    { type: 'human', label: 'Human Readable' },
    { type: 'json', label: 'JSON' },
  ];

  return (
    <div className="mt-6 bg-white p-6 rounded shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Parsed Results</h2>
        <div className="flex items-center">
          {views.map(({ type, label }) => (
            <button
              key={type}
              onClick={() => setView(type)}
              className={`mr-2 px-3 py-1 rounded transition-colors duration-200 ${
                view === type ? 'bg-blue-500 text-white' : 'bg-gray-200 hover:bg-gray-300'
              }`}
              aria-pressed={view === type}
              aria-label={`View parsed results as ${label}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Render the appropriate component based on the selected view */}
      {view === 'human' ? <HumanReadable data={parsingResult} /> : <JsonView data={parsingResult} />}

      {/* Download Button */}
      <div className="mt-4">
        <DownloadButton data={parsingResult} />
      </div>
    </div>
  );
};

export default ResultViewer;
