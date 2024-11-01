// static/js/reducers/parsingReducer.js
const initialState = {
  parsing: false,
  parsedData: null,
  error: null
};

const parsingReducer = (state = initialState, action) => {
  switch (action.type) {
    case 'PARSE_EMAIL_INITIATED':
      return {
        ...state,
        parsing: true,
        error: null
      };
    case 'PARSE_EMAIL_SUCCESS':
      return {
        ...state,
        parsing: false,
        parsedData: action.payload,
        error: null
      };
    case 'PARSE_EMAIL_FAILURE':
      return {
        ...state,
        parsing: false,
        error: action.payload
      };
    default:
      return state;
  }
};

export default parsingReducer;