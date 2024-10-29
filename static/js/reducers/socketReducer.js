// static/js/reducers/socketReducer.js
import { SOCKET_CONNECTED, SOCKET_DISCONNECTED, SOCKET_ERROR, UPDATE_PROGRESS } from '../actions/actionTypes.js';

const initialState = {
  isConnected: false,
  error: null,
  progress: 0,
  disconnectReason: null,
};

const socketReducer = (state = initialState, action) => {
  switch (action.type) {
    case SOCKET_CONNECTED:
      return { ...state, isConnected: true, error: null, disconnectReason: null };
    case SOCKET_DISCONNECTED:
      return { ...state, isConnected: false, disconnectReason: action.payload };
    case SOCKET_ERROR:
      return { ...state, error: action.payload };
    case UPDATE_PROGRESS:
      return { ...state, progress: action.payload.progress };
    default:
      return state;
  }
};

export default socketReducer;
