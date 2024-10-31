// static/js/core/socketListeners.js
import store from '../store';
import { parsingCompleted, parsingError } from '../actions/parsingActions';

export const initializeSocketListeners = (socket) => {
  socket.on('parsing_completed', (data) => {
    store.dispatch(parsingCompleted(data.result));
  });

  socket.on('parsing_error', (error) => {
    store.dispatch(parsingError(error.error));
  });
};