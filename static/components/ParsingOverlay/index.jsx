// static/components/ParsingOverlay/index.jsx
import React, { useState, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import FocusLock from 'react-focus-lock';
import { throttle } from 'lodash';
import ProgressBar from './ProgressBar';
import StatusIndicator from './StatusIndicator';
import './styles.css';

/**
 * Enumeration for parsing statuses
 */
const ParsingStatus = Object.freeze({
  IDLE: 'idle',
  PARSING: 'parsing',
  COMPLETE: 'complete',
  ERROR: 'error',
  RECONNECTING: 'reconnecting',
});

/**
 * ParsingOverlay Component
 * Displays an overlay during the email parsing process with progress and status indicators.
 *
 * @param {Object} props
 * @param {Object} props.socket - Socket.IO client instance
 * @param {boolean} props.active - Whether the overlay is active
 * @param {string} props.emailContent - Content of the email being parsed
 * @param {Function} props.onClose - Callback to close the overlay
 */
const ParsingOverlay = ({ socket, active, emailContent, onClose }) => {
  const [highlights, setHighlights] = useState([]);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState(ParsingStatus.IDLE);
  const [errorMessage, setErrorMessage] = useState('');

  // Throttled handler to manage frequent 'line_parsed' events
  const throttledHandleLineParsed = useCallback(
    throttle((data) => {
      setHighlights((prev) => {
        const updated = [
          ...prev,
          {
            lineNumber: data.line_number,
            content: data.parsed_content,
            section: data.highlight_section,
          },
        ];
        // Limit to last 100 highlights
        return updated.slice(-100);
      });
    }, 100),
    []
  );

  // Handler for socket reconnection attempts
  const handleReconnect = useCallback(() => {
    if (socket && !socket.connected) {
      setStatus(ParsingStatus.RECONNECTING);
      socket.connect();
    }
  }, [socket]);

  useEffect(() => {
    if (!socket) return;

    // Event Handlers
    const handleLineParsed = throttledHandleLineParsed;
    const handleParsingProgress = (data) => {
      setProgress(data.progress);
      setStatus(ParsingStatus.PARSING);
    };
    const handleParsingComplete = () => {
      setProgress(100);
      setStatus(ParsingStatus.COMPLETE);
      setTimeout(() => {
        setStatus(ParsingStatus.IDLE);
        setHighlights([]);
        if (onClose) onClose();
      }, 2000);
    };
    const handleParsingError = (data) => {
      setStatus(ParsingStatus.ERROR);
      setErrorMessage(data.message || 'An unexpected error occurred during parsing.');
    };
    const handleDisconnect = () => {
      setStatus(ParsingStatus.RECONNECTING);
      setErrorMessage('Connection lost. Attempting to reconnect...');
    };
    const handleReconnectAttempt = () => {
      setErrorMessage('Reconnecting...');
    };
    const handleReconnectError = () => {
      setStatus(ParsingStatus.ERROR);
      setErrorMessage('Failed to reconnect. Please try again.');
    };

    // Register Socket Event Listeners
    socket.on('line_parsed', handleLineParsed);
    socket.on('parsing_progress', handleParsingProgress);
    socket.on('parsing_completed', handleParsingComplete);
    socket.on('parsing_error', handleParsingError);
    socket.on('disconnect', handleDisconnect);
    socket.io.on('reconnect_attempt', handleReconnectAttempt);
    socket.io.on('reconnect_error', handleReconnectError);

    // Attempt to reconnect if disconnected
    if (!socket.connected && active) {
      handleReconnect();
    }

    // Keyboard accessibility: Close overlay on 'Esc' key press
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && active) {
        if (onClose) onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      // Cleanup Socket Event Listeners
      socket.off('line_parsed', handleLineParsed);
      socket.off('parsing_progress', handleParsingProgress);
      socket.off('parsing_completed', handleParsingComplete);
      socket.off('parsing_error', handleParsingError);
      socket.off('disconnect', handleDisconnect);
      socket.io.off('reconnect_attempt', handleReconnectAttempt);
      socket.io.off('reconnect_error', handleReconnectError);
      window.removeEventListener('keydown', handleKeyDown);
      throttledHandleLineParsed.cancel();
    };
  }, [socket, active, throttledHandleLineParsed, onClose, handleReconnect]);

  // If not active or idle, do not render the overlay
  if (!active || status === ParsingStatus.IDLE) return null;

  return (
    <div
      className="fixed inset-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="parsingOverlayTitle"
    >
      <FocusLock>
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-3xl mx-4 p-6 relative">
          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100"
            aria-label="Close Parsing Overlay"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          <h2 id="parsingOverlayTitle" className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            {status === ParsingStatus.RECONNECTING ? 'Reconnecting...' : 'Parsing Email'}
          </h2>

          {/* Progress Bar */}
          <ProgressBar progress={progress} />

          {/* Status Indicator */}
          <StatusIndicator status={status} errorMessage={errorMessage} />

          {/* Highlights Container */}
          <div
            className="mt-4 bg-gray-100 dark:bg-gray-800 rounded-lg shadow-inner p-4 max-h-[50vh] overflow-y-auto"
            aria-live="polite"
          >
            <pre className="font-mono text-sm whitespace-pre-wrap">
              {highlights.map((highlight) => (
                <div
                  key={highlight.lineNumber}
                  className={`highlight-${highlight.section.replace(/\s+/g, '')} p-1 mb-1 rounded transition-all duration-300`}
                >
                  {highlight.content}
                </div>
              ))}
            </pre>
          </div>

          {/* Optional: Display email content or additional details */}
          <div className="mt-4">
            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200">Email Content</h3>
            <p className="text-sm text-gray-700 dark:text-gray-300">{emailContent}</p>
          </div>

          {/* Retry Button for Reconnection */}
          {status === ParsingStatus.ERROR && (
            <div className="mt-4 flex justify-center">
              <button
                onClick={() => {
                  if (socket) {
                    socket.connect();
                    setStatus(ParsingStatus.RECONNECTING);
                    setErrorMessage('');
                  }
                }}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                aria-label="Retry Connection"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      </FocusLock>
    </div>
  );
};

// PropTypes for type checking
ParsingOverlay.propTypes = {
  socket: PropTypes.object.isRequired, // Socket.IO client instance
  active: PropTypes.bool.isRequired, // Whether the overlay is active
  emailContent: PropTypes.string.isRequired, // Content of the email being parsed
  onClose: PropTypes.func, // Callback to close the overlay
};

// Default props
ParsingOverlay.defaultProps = {
  onClose: () => {},
};

export default React.memo(ParsingOverlay);
