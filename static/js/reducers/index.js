// static/js/reducers/index.js
import { combineReducers } from 'redux';
import socketReducer from './socketReducer.js';
import parsingReducer from './parsingReducer.js';
import uploadReducer from './uploadReducer.js';
import formReducer from './formReducer.js';
import toastReducer from './toastReducer.js';
import modalReducer from './modalReducer.js';
import themeReducer from './themeReducer.js';
// Import other reducers as needed

const rootReducer = combineReducers({
  socket: socketReducer,
  parsing: parsingReducer,
  upload: uploadReducer,
  form: formReducer,
  toast: toastReducer,
  modal: modalReducer,
  theme: themeReducer,
  // Add other reducers here
});

export default rootReducer;
