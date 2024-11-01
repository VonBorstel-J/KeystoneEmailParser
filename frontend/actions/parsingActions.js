// frontend/actions/parsingActions.js
import { parseEmail as parseEmailAPI } from '../actions/api';
import socketIOClient from 'socket.io-client';
import { setupSocketListeners } from '../core/socketListeners';
import { generateId } from '../utils/helpers';

/**
 * Action to start the parsing process.
 * @param {Object} data - Data required to start parsing.
 */
export const startParsing = (data) => async (dispatch) => {
  dispatch({ type: 'START_PARSING' });

  try {
    // Generate a unique socket ID for this session if not provided
    const socketId = data.socket_id || generateId();
    const socket = socketIOClient('http://localhost:8080', {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
    });

    setupSocketListeners(socket, dispatch); // Attach listeners for socket events

    await parseEmailAPI({ ...data, socket_id: socketId });
    // Parsing is handled via WebSocket events, no need to wait for response from parseEmailAPI
  } catch (error) {
    console.error('Error during parsing start:', error);
    dispatch({
      type: 'SET_ERROR',
      payload: error.response?.data?.error_message || 'Parsing failed. Please try again.',
    });
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
