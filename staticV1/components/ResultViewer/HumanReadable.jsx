// static/components/ResultViewer/HumanReadable.jsx

import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { CopyToClipboard } from 'react-copy-to-clipboard';
import { Clipboard } from 'lucide-react';
import { debounce } from 'lodash';
import './styles.css';

/**
 * Capitalizes the first letter of a string
 * @param {string} string
 * @returns {string}
 */
const capitalizeFirstLetter = (string) => {
  return string.charAt(0).toUpperCase() + string.slice(1);
};

/**
 * Escapes HTML characters to prevent XSS
 * @param {string} text
 * @returns {string}
 */
const escapeHtml = (text) => {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return String(text).replace(/[&<>"']/g, (m) => map[m]);
};

const HumanReadable = ({ data }) => {
  const [activeSection, setActiveSection] = useState(null);
  const [copyStatus, setCopyStatus] = useState(false);

  /**
   * Toggles the visibility of a section.
   * @param {string} section - The section to toggle.
   */
  const toggleSection = (section) => {
    setActiveSection((prev) => (prev === section ? null : section));
  };

  /**
   * Handles the copy action with a debounce to prevent rapid state changes.
   */
  const handleCopy = useMemo(
    () =>
      debounce(() => {
        setCopyStatus(true);
        setTimeout(() => {
          setCopyStatus(false);
        }, 2000);
      }, 300),
    []
  );

  /**
   * Generates the content for a given section.
   * @param {string} section - The section name.
   * @param {any} content - The content of the section.
   * @returns {JSX.Element}
   */
  const renderSectionContent = (section, content) => {
    if (typeof content === 'object' && content !== null) {
      return (
        <ul className="list-disc list-inside">
          {Object.entries(content).map(([key, value]) => (
            <li key={key}>
              <strong>{capitalizeFirstLetter(key)}:</strong> {escapeHtml(String(value))}
            </li>
          ))}
        </ul>
      );
    } else {
      return <p>{escapeHtml(String(content))}</p>;
    }
  };

  /**
   * Prepares the human-readable text for copying.
   * @returns {string}
   */
  const prepareCopyText = () => {
    return Object.entries(data)
      .filter(([section]) => section !== 'originalEmail')
      .map(([section, content]) => {
        const sectionTitle = capitalizeFirstLetter(section);
        if (typeof content === 'object' && content !== null) {
          const items = Object.entries(content)
            .map(([key, value]) => `${capitalizeFirstLetter(key)}: ${value}`)
            .join('\n');
          return `${sectionTitle}:\n${items}`;
        } else {
          return `${sectionTitle}: ${content}`;
        }
      })
      .join('\n\n');
  };

  return (
    <div className="human-readable-view">
      {/* Copy Button */}
      <div className="flex justify-end mb-2">
        <CopyToClipboard text={prepareCopyText()} onCopy={handleCopy}>
          <button
            className="copy-button flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100 transition-colors"
            aria-label="Copy Human-Readable Results"
          >
            <Clipboard className="h-5 w-5 mr-1" />
            {copyStatus ? 'Copied!' : 'Copy'}
          </button>
        </CopyToClipboard>
      </div>

      {Object.entries(data).map(([section, content]) => {
        if (section === 'originalEmail') return null; // Skip original email
        return (
          <div key={section} className="mb-4">
            <button
              onClick={() => toggleSection(section)}
              className="w-full text-left px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 flex justify-between items-center"
              aria-expanded={activeSection === section}
            >
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {capitalizeFirstLetter(section)}
              </span>
              <span className="ml-2">
                {activeSection === section ? '-' : '+'}
              </span>
            </button>
            {activeSection === section && (
              <div className="mt-2 px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-md">
                {renderSectionContent(section, content)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

HumanReadable.propTypes = {
  data: PropTypes.shape({
    originalEmail: PropTypes.string.isRequired,
    // Add other parsed data fields as needed based on importSchema.txt
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

export default React.memo(HumanReadable);
