// static/components/ResultViewer/OriginalView.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { highlightEmailContent, escapeHtml } from '@utils/html.js';

const OriginalView = ({ emailContent }) => {
  const highlightedContent = highlightEmailContent(emailContent);

  return (
    <div
      id="originalEmail"
      className="font-mono text-sm whitespace-pre-wrap"
      dangerouslySetInnerHTML={{ __html: highlightedContent }}
    ></div>
  );
};

OriginalView.propTypes = {
  emailContent: PropTypes.string.isRequired,
};

export default OriginalView;
