// static/js/reducers/socketReducer.js
import { SET_SOCKET_CONNECTED, SET_SOCKET_DISCONNECTED, SET_SOCKET_ERROR } from '@actions/actionTypes.js';

const initialState = {
  isConnected: false,
  error: null,
  socketInstance: null, // To store the socket instance if needed
};

const socketReducer = (state = initialState, action) => {
  switch (action.type) {
    case SET_SOCKET_CONNECTED:
      return {
        ...state,
        isConnected: true,
        error: null,
      };
    case SET_SOCKET_DISCONNECTED:
      return {
        ...state,
        isConnected: false,
      };
    case SET_SOCKET_ERROR:
      return {
        ...state,
        error: action.payload,
      };
    default:
      return state;
  }
};

export default socketReducer;
