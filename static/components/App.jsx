// static/components/App.jsx

import React from 'react';
import { Provider } from 'react-redux';
import store from '../js/store';
import EmailParser from './EmailParser';


function App() {
  return (
    <Provider store={store}>
      <ErrorBoundary>
        <EmailParser />
      </ErrorBoundary>
    </Provider>
  );
}

export default App;
