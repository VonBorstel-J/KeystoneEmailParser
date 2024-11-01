// static/components/ParsingOverlay/StatusIndicator.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { AlertCircle, CheckCircle } from 'lucide-react';

/**
 * StatusIndicator Component
 * Displays different status messages based on the current parsing status.
 *
 * @param {Object} props
 * @param {string} props.status - Current status ('parsing', 'complete', 'error')
 * @param {string} [props.errorMessage] - Error message to display in case of 'error' status
 */
const StatusIndicator = ({ status, errorMessage }) => {
  const renderStatus = () => {
    switch(status) {
      case 'parsing':
        return (
          <div className="flex items-center gap-2 mb-4 text-blue-600" role="status">
            <AlertCircle className="w-5 h-5" />
            <span>Parsing in progress...</span>
          </div>
        );
      case 'complete':
        return (
          <div className="flex items-center gap-2 mb-4 text-green-600" role="status">
            <CheckCircle className="w-5 h-5" />
            <span>Parsing complete!</span>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center gap-2 mb-4 text-red-600" role="alert">
            <AlertCircle className="w-5 h-5" />
            <span>{errorMessage || 'Error occurred during parsing'}</span>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <>
      {renderStatus()}
    </>
  );
};

StatusIndicator.propTypes = {
  status: PropTypes.oneOf(['parsing', 'complete', 'error']).isRequired,
  errorMessage: PropTypes.string,
};

StatusIndicator.defaultProps = {
  errorMessage: '',
};

export default React.memo(StatusIndicator);
