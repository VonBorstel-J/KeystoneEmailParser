// static/js/store.js
import { createStore, combineReducers, applyMiddleware, compose } from 'redux';
import thunk from 'redux-thunk';
import formReducer from './reducers/formReducer.js';
import parsingReducer from './reducers/parsingReducer.js';
import uploadReducer from './reducers/uploadReducer.js';
import socketReducer from './reducers/socketReducer.js';

const rootReducer = combineReducers({
  form: formReducer,
  parsing: parsingReducer,
  upload: uploadReducer,
  socket: socketReducer,
  // Add other reducers here if needed
});

const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;

const store = createStore(
  rootReducer,
  composeEnhancers(applyMiddleware(thunk))
);

export default store;
