// static/js/reducers/parsingReducer.js
import { START_PARSING, UPDATE_PARSING_PROGRESS, PARSING_COMPLETE, PARSING_ERROR } from '../actions/actionTypes.js';

const initialState = {
  isParsing: false,
  progress: 0,
  error: null,
};

const parsingReducer = (state = initialState, action) => {
  switch (action.type) {
    case START_PARSING:
      return { ...state, isParsing: true, progress: 0, error: null };
    case UPDATE_PARSING_PROGRESS:
      return { ...state, progress: action.payload };
    case PARSING_COMPLETE:
      return { ...state, isParsing: false, progress: 100, error: null };
    case PARSING_ERROR:
      return { ...state, isParsing: false, error: action.payload };
    default:
      return state;
  }
};

export default parsingReducer;
