// static/js/actions/socketActions.js
import { SET_SOCKET_CONNECTED, SET_SOCKET_DISCONNECTED, SET_SOCKET_ERROR } from './actionTypes.js';
import { showToast } from './toastActions.js';

export const setSocketConnected = () => ({
  type: SET_SOCKET_CONNECTED,
});

export const setSocketDisconnected = () => ({
  type: SET_SOCKET_DISCONNECTED,
});

export const setSocketError = (error) => ({
  type: SET_SOCKET_ERROR,
  payload: error,
});
