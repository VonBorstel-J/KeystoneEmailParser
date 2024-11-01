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
  console.log('DOM Content Loaded');
  try {
    // Initialize managers
    console.log('Initializing managers...');
    themeManager.initialize();
    validationManager.initialize();

    // Initialize Socket Manager with options
    console.log('Initializing socket...');
    const socket = socketManager.getSocket(socketOptions);

    // Initialize Parser
    console.log('Initializing parser...');
    const parser = new Parser(socket);

    // Initialize Socket Listeners
    console.log('Initializing socket listeners...');
    initializeSocketListeners(socket, store);

    // Mount the React Application
    console.log('Mounting React application...');
    const container = document.getElementById('root');
    if (!container) {
      throw new Error('Root container not found!');
    }
    const root = createRoot(container);
    root.render(
      <React.StrictMode>
        <Provider store={store}>
          <App />
        </Provider>
      </React.StrictMode>
    );
    console.log('React application mounted successfully');
  } catch (error) {
    console.error('Initialization error:', error);
  }
});

// Handle hot module replacement
if (module.hot) {
  module.hot.accept();
}

