// static/js/reducers/parsingReducer.js
import {
  START_PARSING,
  UPDATE_PARSING_PROGRESS,
  PARSING_SUCCESS,
  PARSING_FAILURE,
} from '@actions/actionTypes.js';

const initialState = {
  isOverlayActive: false,
  loadingMessage: 'Processing...',
  progress: 0,
  status: 'idle', // 'parsing', 'completed', 'error'
  results: null,
  error: null,
};

const parsingReducer = (state = initialState, action) => {
  switch (action.type) {
    case START_PARSING:
      return {
        ...state,
        isOverlayActive: true,
        progress: 0,
        status: 'parsing',
        results: null,
        error: null,
      };
    case UPDATE_PARSING_PROGRESS:
      return {
        ...state,
        progress: action.payload,
      };
    case PARSING_SUCCESS:
      return {
        ...state,
        isOverlayActive: false,
        progress: 100,
        status: 'completed',
        results: action.payload,
      };
    case PARSING_FAILURE:
      return {
        ...state,
        isOverlayActive: false,
        progress: 0,
        status: 'error',
        error: action.payload,
      };
    default:
      return state;
  }
};

export default parsingReducer;
