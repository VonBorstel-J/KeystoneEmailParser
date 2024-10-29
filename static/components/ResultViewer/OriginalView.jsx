// static/components/ResultViewer/OriginalView.jsx

import React from 'react';
import PropTypes from 'prop-types';

/**
 * OriginalView Component
 * Displays the original email content.
 *
 * @param {Object} props
 * @param {string} props.emailContent - The original email content.
 */
const OriginalView = ({ emailContent }) => (
  <div className="original-view font-mono text-sm whitespace-pre-wrap dark:text-gray-300">
    {emailContent}
  </div>
);

OriginalView.propTypes = {
  emailContent: PropTypes.string.isRequired,
};

export default React.memo(OriginalView);
