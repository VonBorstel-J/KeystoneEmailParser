import { io } from 'socket.io-client';

const SOCKET_OPTIONS = {
  path: '/socket.io',
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  timeout: 60000,
  forceNew: true,
  autoConnect: false
};

class SocketManager {
  constructor() {
    this.socket = null;
    this.isConnecting = false;
    this.eventHandlers = new Map();
    this.debugMode = true; // Enable debug logging
  }

  async connect() {
    if (this.isConnecting) {
      this.log('Connection attempt already in progress');
      return this.socket;
    }
    if (this.socket?.connected) {
      this.log('Already connected');
      return this.socket;
    }

    this.isConnecting = true;
    
    try {
      this.log('Initiating socket connection');
      this.socket = io('http://127.0.0.1:5000', SOCKET_OPTIONS);
      
      // Reattach event handlers
      this.eventHandlers.forEach((handlers, event) => {
        handlers.forEach(handler => {
          this.socket.on(event, handler);
        });
      });

      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Socket connection timeout'));
        }, 5000);

        this.socket.once('connect', () => {
          clearTimeout(timeout);
          this.log('Socket connected successfully');
          resolve();
        });

        this.socket.once('connect_error', (error) => {
          clearTimeout(timeout);
          this.log('Socket connection error:', error);
          reject(error);
        });
      });

      return this.socket;
    } catch (error) {
      this.log('Socket connection failed:', error);
      throw error;
    } finally {
      this.isConnecting = false;
    }
  }

  on(event, handler) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event).add(handler);
    
    if (this.socket) {
      this.socket.on(event, handler);
    }
    this.log(`Registered handler for event: ${event}`);
  }

  off(event, handler) {
    if (this.eventHandlers.has(event)) {
      this.eventHandlers.get(event).delete(handler);
    }
    if (this.socket) {
      this.socket.off(event, handler);
    }
    this.log(`Removed handler for event: ${event}`);
  }

  emit(event, ...args) {
    if (this.socket?.connected) {
      this.log(`Emitting event: ${event}`, args);
      this.socket.emit(event, ...args);
    } else {
      this.log(`Failed to emit event ${event}: Socket not connected`);
    }
  }

  getId() {
    return this.socket?.id;
  }

  isConnected() {
    return this.socket?.connected || false;
  }

  log(...args) {
    if (this.debugMode) {
      console.log('[SocketManager]', ...args);
    }
  }
}

const socketManager = new SocketManager();
export default socketManager;