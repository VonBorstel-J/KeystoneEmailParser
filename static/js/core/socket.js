import io from 'socket.io-client';
import store from '../store.js';
import { setSocketConnected, setSocketDisconnected, setSocketError } from '../actions/socketActions.js';

class SocketManager {
  constructor() {
    if (!SocketManager.instance) {
      this.socket = null;
      SocketManager.instance = this;
    }
    return SocketManager.instance;
  }

  getSocket(options = {}) {
    if (!this.socket) {
      const defaultOptions = {
        transports: ['websocket'],
        path: '/socket.io/',
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        timeout: 20000
      };

      const socketUrl = process.env.NODE_ENV === 'production' 
        ? window.location.origin
        : 'http://localhost:5000';

      this.socket = io(socketUrl, { ...defaultOptions, ...options });

      this.socket.on('connect', () => {
        store.dispatch(setSocketConnected());
        console.log('Socket connected');
      });

      this.socket.on('disconnect', () => {
        store.dispatch(setSocketDisconnected());
        console.log('Socket disconnected');
      });

      this.socket.on('connect_error', (error) => {
        store.dispatch(setSocketError(error.message));
        console.error('Socket connection error:', error);
      });
    }
    return this.socket;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

const socketManager = new SocketManager();
export default socketManager;