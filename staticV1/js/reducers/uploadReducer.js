// static/js/reducers/uploadReducer.js
import { UPLOAD_START, UPLOAD_PROGRESS, UPLOAD_COMPLETE, UPLOAD_ERROR } from '../actions/actionTypes.js';

const initialState = {
  isUploading: false,
  progress: 0,
  error: null,
};

const uploadReducer = (state = initialState, action) => {
  switch (action.type) {
    case UPLOAD_START:
      return { ...state, isUploading: true, progress: 0, error: null };
    case UPLOAD_PROGRESS:
      return { ...state, progress: action.payload };
    case UPLOAD_COMPLETE:
      return { ...state, isUploading: false, progress: 100, error: null };
    case UPLOAD_ERROR:
      return { ...state, isUploading: false, error: action.payload };
    default:
      return state;
  }
};

export default uploadReducer;
