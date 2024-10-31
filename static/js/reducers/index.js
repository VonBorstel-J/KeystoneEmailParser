// static/js/reducers/index.js
import { combineReducers } from 'redux';
import parsingReducer from './parsingReducer';
import socketReducer from './socketReducer';
import modalReducer from './modalReducer';
import toastReducer from './toastReducer';
import themeReducer from './themeReducer';
import formReducer from './formReducer';
import uploadReducer from './uploadReducer';

const rootReducer = combineReducers({
  parsing: parsingReducer,
  socket: socketReducer,
  modal: modalReducer,
  toast: toastReducer,
  theme: themeReducer,
  form: formReducer,
  upload: uploadReducer
});

export default rootReducer;