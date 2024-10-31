// static/js/core/socket.js

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
        timeout: 20000,
      };

      if (typeof io !== 'undefined') {
        const socketUrl = process.env.NODE_ENV === 'production' 
          ? window.location.origin 
          : 'http://localhost:5000';

        this.socket = io(socketUrl, { ...defaultOptions, ...options });

        this.socket.on('connect', () => {
          console.log('Socket connected');
        });

        this.socket.on('disconnect', () => {
          console.log('Socket disconnected');
        });

        this.socket.on('connect_error', (error) => {
          console.error('Socket connection error:', error);
          
        });

        this.socket.on('connect_timeout', () => {
          console.error('Socket connection timed out');
          
        });
      } else {
        console.error('Socket.IO client not loaded');
      }
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
