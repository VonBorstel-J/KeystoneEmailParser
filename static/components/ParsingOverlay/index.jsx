// static/components/ParsingOverlay/index.jsx
import React from 'react';
import PropTypes from 'prop-types';
import FocusLock from 'react-focus-lock';
import ProgressBar from './ProgressBar';
import StatusIndicator from './StatusIndicator';
import './styles.css';

const ParsingOverlay = ({ isActive, progress, status, message, onClose }) => {
  if (!isActive) return null;

  return (
    <div className="fixed inset-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <FocusLock>
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-3xl mx-4 p-6">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Parsing Email
          </h2>
          <ProgressBar progress={progress} />
          <StatusIndicator status={status} message={message} />
          {onClose && (
            <button
              onClick={onClose}
              className="mt-4 px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-md"
            >
              Close
            </button>
          )}
        </div>
      </FocusLock>
    </div>
  );
};

ParsingOverlay.propTypes = {
  isActive: PropTypes.bool.isRequired,
  progress: PropTypes.number,
  status: PropTypes.string,
  message: PropTypes.string,
  onClose: PropTypes.func,
};

ParsingOverlay.defaultProps = {
  progress: 0,
  status: 'idle',
  message: '',
  onClose: null,
};

export default ParsingOverlay;

