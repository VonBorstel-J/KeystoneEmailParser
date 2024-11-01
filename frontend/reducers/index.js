// frontend/reducers/index.js
import { createStore, applyMiddleware, combineReducers, compose } from 'redux';
import thunk from 'redux-thunk';
import parsingReducer from './parsingReducer';

/**
 * Root reducer combining all individual reducers.
 */
const rootReducer = combineReducers({
  parsing: parsingReducer,
});

// Custom middleware to handle and log errors during action dispatching
const errorHandlingMiddleware = (store) => (next) => (action) => {
  try {
    return next(action);
  } catch (error) {
    console.error('Error during action dispatch:', action, error);
    return store.dispatch({ type: 'SET_ERROR', payload: 'Something went wrong during state update.' });
  }
};

// Enable Redux DevTools Extension if available, with fallback for compose
const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;

/**
 * Redux store configured with thunk middleware, error handling, and DevTools extension.
 */
const store = createStore(
  rootReducer,
  composeEnhancers(applyMiddleware(thunk, errorHandlingMiddleware))
);

export default store;
