// static/js/core/socketListeners.js
import {
    setSocketConnected,
    setSocketDisconnected,
    setSocketError,
  } from '../actions/socketActions.js';
  import { showToast } from '../actions/toastActions.js';
  import {
    updateParsingProgress,
    parsingSuccess,
    parsingFailure,
  } from '../actions/parsingActions.js';
  
  export const initializeSocketListeners = (socket, store) => {
    socket.on('connect', () => {
      store.dispatch(setSocketConnected());
      store.dispatch(showToast('success', 'Connected to server.'));
    });
  
    socket.on('disconnect', () => {
      store.dispatch(setSocketDisconnected());
      store.dispatch(showToast('error', 'Disconnected from server.'));
    });
  
    socket.on('error', (error) => {
      store.dispatch(setSocketError(error));
      store.dispatch(showToast('error', `Socket error: ${error}`));
    });
  
    socket.on('parsing_progress', (data) => {
      store.dispatch(updateParsingProgress(data.progress));
    });
  
    socket.on('parsing_complete', (data) => {
      store.dispatch(parsingSuccess(data.results));
      store.dispatch(showToast('success', 'Parsing completed successfully.'));
    });
  
    socket.on('parsing_error', (error) => {
      store.dispatch(parsingFailure(error));
      store.dispatch(showToast('error', `Parsing error: ${error}`));
    });
  
    // Add more socket event listeners as needed
  };
  