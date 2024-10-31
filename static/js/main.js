import React from 'react';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import store from './store.js';
import App from '@components/App.jsx';
import socketManager from '@core/socket.js';
import Parser from '@core/parser.js';
import validationManager from '@core/validation.js';
import themeManager from '@core/theme.js';
import { setSocketConnected, setSocketDisconnected } from '@actions/socketActions.js';
import { initializeSocketListeners } from '@core/socketListeners.js';

// Import CSS files
import '../css/styles.css';
import '../css/utilities.css';


// Initialize socket connection options
const socketOptions = {
  transports: ['websocket'],
  path: '/socket.io/',
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000
};

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
  try {
    // Initialize managers
    themeManager.initialize();
    validationManager.initialize();

    // Initialize Socket Manager with options
    const socket = socketManager.getSocket(socketOptions);

    // Initialize Parser
    const parser = new Parser(socket);

    // Initialize Socket Listeners
    initializeSocketListeners(socket, store);

    // Mount the React Application
    const container = document.getElementById('root');
    const root = createRoot(container);
    root.render(
      <Provider store={store}>
        <App />
      </Provider>
    );
  } catch (error) {
    console.error('Initialization error:', error);
  }
});

// Handle hot module replacement
if (module.hot) {
  module.hot.accept();
}
