// static/js/reducers/socketReducer.js
const initialState = {
  socket: null,
  isConnected: false,
};

const socketReducer = (state = initialState, action) => {
  switch (action.type) {
    case 'SOCKET_CONNECTED':
      return { ...state, socket: action.payload, isConnected: true };
    case 'SOCKET_DISCONNECTED':
      return { ...state, socket: null, isConnected: false };
    default:
      return state;
  }
};

export default socketReducer;
