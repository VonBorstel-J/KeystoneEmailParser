// static/components/ResultViewer/index.jsx

import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { CopyToClipboard } from 'react-copy-to-clipboard';
import { saveAs } from 'file-saver';
import { jsPDF } from 'jspdf';
import JsonView from './JsonView.jsx';
import HumanReadable from './HumanReadable.jsx';
import OriginalView from './OriginalView.jsx';
import { Clipboard, Download, FileText } from 'lucide-react';
import './styles.css';

/**
 * Utility function to convert JSON to CSV.
 * @param {Object} json - The JSON data to convert.
 * @returns {string} - The CSV representation of the JSON data.
 */
const jsonToCsv = (json) => {
  const items = Array.isArray(json) ? json : [json];
  if (items.length === 0) return '';

  const headers = Object.keys(items[0]);
  const csvRows = [
    headers.join(','), // Header row
    ...items.map((item) =>
      headers.map((header) => `"${item[header] || ''}"`).join(',')
    ),
  ];

  return csvRows.join('\n');
};

const ResultViewer = ({ parsedData }) => {
  const [activeTab, setActiveTab] = useState('json'); // 'json', 'human', or 'original'
  const [copyStatus, setCopyStatus] = useState({
    json: false,
    human: false,
    original: false,
  });

  // Memoize CSV conversion for performance
  const csvData = useMemo(() => jsonToCsv(parsedData), [parsedData]);

  /**
   * Handles the export of data to CSV.
   */
  const handleExportCsv = () => {
    const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
    saveAs(blob, 'parsed_results.csv');
  };

  /**
   * Handles the export of data to PDF.
   */
  const handleExportPdf = () => {
    const doc = new jsPDF();
    doc.text(JSON.stringify(parsedData, null, 2), 10, 10);
    doc.save('parsed_results.pdf');
  };

  /**
   * Handles the copy action and resets the copy status after a delay.
   * @param {string} tab - The current active tab.
   */
  const handleCopy = (tab) => {
    setCopyStatus((prev) => ({ ...prev, [tab]: true }));
    setTimeout(() => {
      setCopyStatus((prev) => ({ ...prev, [tab]: false }));
    }, 2000);
  };

  /**
   * Renders the appropriate content based on the active tab.
   */
  const renderContent = () => {
    switch (activeTab) {
      case 'json':
        return <JsonView data={parsedData} />;
      case 'human':
        return <HumanReadable data={parsedData} />;
      case 'original':
        return <OriginalView emailContent={parsedData.originalEmail} />;
      default:
        return null;
    }
  };

  /**
   * Renders the copy button based on the active tab.
   */
  const renderCopyButton = () => {
    return (
      <CopyToClipboard
        text={
          activeTab === 'json'
            ? JSON.stringify(parsedData, null, 2)
            : activeTab === 'human'
            ? parsedData.humanReadable
            : parsedData.originalEmail
        }
        onCopy={() => handleCopy(activeTab)}
      >
        <button
          className="copy-button flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100 transition-colors"
          aria-label="Copy Results"
        >
          <Clipboard className="h-5 w-5 mr-1" />
          {copyStatus[activeTab] ? 'Copied!' : 'Copy'}
        </button>
      </CopyToClipboard>
    );
  };

  /**
   * Renders the export buttons for CSV and PDF.
   */
  const renderExportButtons = () => {
    return (
      <div className="export-buttons flex space-x-2 mt-4">
        <button
          onClick={handleExportCsv}
          className="export-btn flex items-center px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
          aria-label="Export as CSV"
        >
          <Download className="h-5 w-5 mr-2" />
          Export CSV
        </button>
        <button
          onClick={handleExportPdf}
          className="export-btn flex items-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
          aria-label="Export as PDF"
        >
          <FileText className="h-5 w-5 mr-2" />
          Export PDF
        </button>
      </div>
    );
  };

  return (
    <div className="result-viewer bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Parsed Results</h2>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 mb-4">
        <nav className="-mb-px flex space-x-8" aria-label="Results Tabs">
          <button
            onClick={() => setActiveTab('json')}
            className={`tab-btn whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'json'
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100'
            }`}
            aria-selected={activeTab === 'json'}
            role="tab"
          >
            JSON
          </button>
          <button
            onClick={() => setActiveTab('human')}
            className={`tab-btn whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'human'
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100'
            }`}
            aria-selected={activeTab === 'human'}
            role="tab"
          >
            Human-Readable
          </button>
          <button
            onClick={() => setActiveTab('original')}
            className={`tab-btn whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'original'
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100'
            }`}
            aria-selected={activeTab === 'original'}
            role="tab"
          >
            Original
          </button>
        </nav>
      </div>

      {/* Copy and Export Controls */}
      <div className="flex justify-between items-center mb-4">
        {renderCopyButton()}
        {activeTab !== 'original' && renderExportButtons()}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {renderContent()}
      </div>
    </div>
  );
};

ResultViewer.propTypes = {
  parsedData: PropTypes.shape({
    originalEmail: PropTypes.string.isRequired,
    humanReadable: PropTypes.string.isRequired,
    // Add other parsed data fields as needed based on importSchema.txt
    // For example:
    requestingParty: PropTypes.shape({
      insuranceCompany: PropTypes.string,
      handler: PropTypes.string,
      carrierClaimNumber: PropTypes.string,
    }),
    insuredInformation: PropTypes.shape({
      name: PropTypes.string,
      contactNumber: PropTypes.string,
      lossAddress: PropTypes.string,
      publicAdjuster: PropTypes.string,
      ownershipStatus: PropTypes.string, // Owner or Tenant
    }),
    adjusterInformation: PropTypes.shape({
      adjusterName: PropTypes.string,
      adjusterPhoneNumber: PropTypes.string,
      adjusterEmail: PropTypes.string,
      jobTitle: PropTypes.string,
      address: PropTypes.string,
      policyNumber: PropTypes.string,
    }),
    assignmentInformation: PropTypes.shape({
      dateOfLoss: PropTypes.string,
      causeOfLoss: PropTypes.string,
      factsOfLoss: PropTypes.string,
      lossDescription: PropTypes.string,
      residenceOccupiedDuringLoss: PropTypes.string,
      wasSomeoneHome: PropTypes.string,
      repairOrMitigationProgress: PropTypes.string,
      type: PropTypes.string,
      inspectionType: PropTypes.string,
      assignmentType: PropTypes.arrayOf(PropTypes.string), // ['Wind', 'Structural', ...]
      additionalDetails: PropTypes.string,
      attachments: PropTypes.arrayOf(PropTypes.string), // URLs or file names
    }),
  }).isRequired,
};

export default React.memo(ResultViewer);
