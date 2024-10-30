// static/components/ResultViewer/DownloadButton.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { useSelector } from 'react-redux';
import { toCSV, formatJSON } from '@utils/format.js';
import { jsPDF } from 'jspdf';

const DownloadButton = ({ type }) => {
  const results = useSelector((state) => state.parsing.results);

  const handleDownload = () => {
    if (!results) {
      alert('No parsed data available to download.');
      return;
    }

    if (type === 'csv') {
      downloadCSV();
    } else if (type === 'pdf') {
      downloadPDF();
    }
  };

  const downloadCSV = () => {
    const csvData = toCSV(results);
    const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    const timestamp = new Date().toISOString().replace(/[:\-T.]/g, '').split('Z')[0];
    link.setAttribute('download', `parsed_emails_${timestamp}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const downloadPDF = () => {
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text('Parsed Email Data', 10, 10);
    doc.setFontSize(12);
    const jsonString = JSON.stringify(results, null, 2);
    const lines = doc.splitTextToSize(jsonString, 180);
    doc.text(lines, 10, 20);
    doc.save(`parsed_emails_${new Date().toISOString().split('T')[0]}.pdf`);
  };

  return (
    <button
      onClick={handleDownload}
      className="flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
      aria-label={`Download ${type.toUpperCase()}`}
    >
      <svg
        className="mr-2 h-5 w-5 text-gray-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        {/* SVG Path based on type */}
        {type === 'csv' ? (
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        ) : (
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        )}
      </svg>
      Download {type.toUpperCase()}
    </button>
  );
};

DownloadButton.propTypes = {
  type: PropTypes.oneOf(['csv', 'pdf']).isRequired,
};

export default DownloadButton;
