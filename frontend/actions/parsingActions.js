// frontend/actions/parsingActions.js
import { parseEmail as parseEmailAPI } from '../actions/api';
import { setupSocketListeners } from '../core/socketListeners';
import socketManager from '../utils/socket';

/**
 * Action to start the parsing process.
 * @param {Object} data - Data required to start parsing.
 */
export const startParsing = (data) => async (dispatch) => {
  dispatch({ type: 'START_PARSING' });

  let socket = null;
  
  try {
    // Connect socket first
    socket = await socketManager.connect();
    
    if (!socket.connected) {
      throw new Error('Failed to establish socket connection');
    }

    // Set up socket listeners
    setupSocketListeners(socket, dispatch);

    // Create form data with socket ID
    const formData = new FormData();
    if (data.email_content) formData.append('email_content', data.email_content);
    if (data.document_image) formData.append('document_image', data.document_image);
    formData.append('parser_option', data.parser_option);
    formData.append('socket_id', socket.id);

    // Make API call
    const response = await parseEmailAPI(formData);

    if (!response.success) {
      throw new Error(response.message || 'Failed to start parsing');
    }

  } catch (error) {
    console.error('Error during parsing start:', error);
    dispatch({
      type: 'SET_ERROR',
      payload: error.message || 'Failed to start parsing. Please try again.'
    });
    
    // Clean up socket on error
    if (socket) {
      socketManager.disconnect();
    }
  }
};

/**
 * Action to update parsing progress.
 * @param {Object} progress - Progress data.
 */
export const updateProgress = (progress) => {
  try {
    return {
      type: 'UPDATE_PROGRESS',
      payload: progress,
    };
  } catch (error) {
    console.error('Error updating parsing progress:', error);
    return {
      type: 'SET_ERROR',
      payload: 'Failed to update progress.',
    };
  }
};

/**
 * Action to complete parsing with results.
 * @param {Object} result - Parsed data.
 */
export const completeParsing = (result) => {
  try {
    return {
      type: 'COMPLETE_PARSING',
      payload: result,
    };
  } catch (error) {
    console.error('Error completing parsing:', error);
    return {
      type: 'SET_ERROR',
      payload: 'Failed to complete parsing process.',
    };
  }
};

/**
 * Action to set an error message.
 * @param {string} error - Error message.
 */
export const setError = (error) => {
  try {
    return {
      type: 'SET_ERROR',
      payload: error,
    };
  } catch (error) {
    console.error('Error setting error message:', error);
    return {
      type: 'SET_ERROR',
      payload: 'An unknown error occurred while setting the error message.',
    };
  }
};

/**
 * Action to add a toast notification.
 * @param {Object} toast - Toast data.
 */
export const addToast = (toast) => {
  try {
    return {
      type: 'ADD_TOAST',
      payload: toast,
    };
  } catch (error) {
    console.error('Error adding toast notification:', error);
    return {
      type: 'SET_ERROR',
      payload: 'Failed to add toast notification.',
    };
  }
};

/**
 * Action to remove a toast notification.
 * @param {string} id - Toast ID to remove.
 */
export const removeToast = (id) => {
  try {
    return {
      type: 'REMOVE_TOAST',
      payload: id,
    };
  } catch (error) {
    console.error('Error removing toast notification:', error);
    return {
      type: 'SET_ERROR',
      payload: 'Failed to remove toast notification.',
    };
  }
};
