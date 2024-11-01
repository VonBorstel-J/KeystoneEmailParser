// frontend/components/ResultViewer/DownloadButton.jsx
import React from 'react';
import { saveAs } from 'file-saver';

/**
 * DownloadButton component enables downloading the parsed data as a JSON file.
 * @param {Object} props - Component properties.
 * @param {Object} props.data - The parsed data to download.
 */
const DownloadButton = ({ data }) => {
  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    saveAs(blob, 'parsed_result.json');
  };

  return (
    <button onClick={handleDownload} className="mt-4 bg-green-500 text-white px-4 py-2 rounded">
      Download JSON
    </button>
  );
};

export default DownloadButton;
