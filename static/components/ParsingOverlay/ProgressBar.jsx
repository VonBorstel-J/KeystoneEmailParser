// static/components/ParsingOverlay/ProgressBar.jsx
import React from 'react';
import PropTypes from 'prop-types';

/**
 * ProgressBar Component
 * Displays a progress bar based on the current progress percentage.
 *
 * @param {Object} props
 * @param {number} props.progress - Progress percentage (0-100)
 */
const ProgressBar = ({ progress }) => {
  return (
    <div className="w-full h-2 bg-gray-200 rounded-full mb-4" aria-label="Parsing Progress">
      <div 
        className="h-full bg-blue-600 rounded-full transition-all duration-300"
        style={{ width: `${progress}%` }}
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin="0"
        aria-valuemax="100"
      />
    </div>
  );
};

ProgressBar.propTypes = {
  progress: PropTypes.number.isRequired,
};

export default React.memo(ProgressBar);
