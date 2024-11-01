// frontend/core/socketListeners.js
import { updateProgress, completeParsing, setError, addToast, removeToast } from '../actions/parsingActions';

/**
 * Sets up socket listeners for parsing events.
 * @param {Socket} socket - The Socket.IO client instance.
 * @param {Function} dispatch - Redux dispatch function.
 */
export const setupSocketListeners = (socket, dispatch) => {
  if (!socket || typeof socket.on !== 'function') {
    console.error("Invalid socket instance provided.");
    dispatch(setError('Socket connection error. Please refresh and try again.'));
    return;
  }

  try {
    socket.on('parsing_started', (data) => {
      try {
        const toastId = Date.now();
        dispatch(addToast({ id: toastId, message: 'Parsing started', type: 'success' }));
        // Remove toast after 3 seconds
        setTimeout(() => dispatch(removeToast(toastId)), 3000);
      } catch (err) {
        console.error("Error handling 'parsing_started' event: ", err);
        dispatch(setError('An error occurred while starting the parsing process.'));
      }
    });

    socket.on('parsing_progress', (data) => {
      try {
        if (!data || typeof data.progress === 'undefined') {
          throw new Error('Invalid progress data received.');
        }
        dispatch(updateProgress(data));
      } catch (err) {
        console.error("Error handling 'parsing_progress' event: ", err);
        dispatch(setError('An error occurred while updating parsing progress.'));
      }
    });

    socket.on('parsing_completed', (data) => {
      try {
        if (!data || !data.result) {
          throw new Error('Invalid completion data received.');
        }
        dispatch(completeParsing(data.result));

        const toastId = Date.now();
        dispatch(addToast({ id: toastId, message: 'Parsing completed', type: 'success' }));
        setTimeout(() => dispatch(removeToast(toastId)), 3000);
      } catch (err) {
        console.error("Error handling 'parsing_completed' event: ", err);
        dispatch(setError('An error occurred while completing the parsing process.'));
      }
    });

    socket.on('parsing_error', (data) => {
      try {
        if (!data || !data.error) {
          throw new Error('Invalid error data received.');
        }
        dispatch(setError(data.error));

        const toastId = Date.now();
        dispatch(addToast({ id: toastId, message: `Error: ${data.error}`, type: 'error' }));
        setTimeout(() => dispatch(removeToast(toastId)), 3000);
      } catch (err) {
        console.error("Error handling 'parsing_error' event: ", err);
        dispatch(setError('An unexpected error occurred during parsing.'));
      }
    });

  } catch (err) {
    console.error("Error setting up socket listeners: ", err);
    dispatch(setError('Failed to setup socket listeners. Please try again.'));
  }
};
