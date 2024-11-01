// frontend\index.js


import React from 'react';
import { createRoot } from 'react-dom/client'; // Updated to correct import from 'react-dom/client'
import { Provider } from 'react-redux';
import App from './App';
import store from './reducers';
import ErrorBoundary from './components/ErrorBoundary';

const container = document.getElementById('root');

// Make sure the container exists before trying to create a root
if (container) {
  const root = createRoot(container);

  root.render(
    <React.StrictMode>
      <Provider store={store}>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </Provider>
    </React.StrictMode>
  );
} else {
  console.error('Root container not found. Unable to initialize the application.');
}
