// static/js/core/socket.js
import io from 'socket.io-client';
import store from '../store.js';
import { setSocketConnected, setSocketDisconnected, setSocketError } from '../actions/socketActions.js';

class SocketManager {
  constructor() {
    this.socket = io();
    this.setupListeners();
  }

  setupListeners() {
    this.socket.on('connect', this.handleConnect.bind(this));
    this.socket.on('disconnect', this.handleDisconnect.bind(this));
    this.socket.on('connect_error', this.handleError.bind(this));
  }

  handleConnect() {
    store.dispatch(setSocketConnected(true));
    this.enableInterface();
  }

  handleDisconnect(reason) {
    store.dispatch(setSocketDisconnected(reason));
    this.disableInterface();
  }

  handleError(error) {
    store.dispatch(setSocketError(error));
    this.disableInterface();
  }

  enableInterface() {
    const elements = document.querySelectorAll('.socket-dependent');
    elements.forEach(el => el.classList.remove('disabled'));
  }

  disableInterface() {
    const elements = document.querySelectorAll('.socket-dependent');
    elements.forEach(el => el.classList.add('disabled'));
  }

  getSocket() {
    return this.socket;
  }
}

const socketManager = new SocketManager();
export default socketManager;
