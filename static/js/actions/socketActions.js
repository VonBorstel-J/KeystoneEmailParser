// static/js/actions/socketActions.js

import { SOCKET_CONNECTED, SOCKET_DISCONNECTED, SOCKET_ERROR, UPDATE_PROGRESS } from './actionTypes';

export const socketConnected = () => ({
  type: SOCKET_CONNECTED,
});

export const socketDisconnected = (reason) => ({
  type: SOCKET_DISCONNECTED,
  payload: reason,
});

export const socketError = (error) => ({
  type: SOCKET_ERROR,
  payload: error,
});

export const updateProgress = (data) => ({
  type: UPDATE_PROGRESS,
  payload: data,
});
