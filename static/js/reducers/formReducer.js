// static/js/reducers/formReducer.js
import { UPDATE_FORM_FIELD, RESET_FORM, FORM_ERROR } from '../actions/actionTypes.js';

const initialState = {
  fields: {
    emailContent: '',
    parserOption: '',
    documentImage: null,
    // Add other form fields as needed
  },
  error: null,
};

const formReducer = (state = initialState, action) => {
  switch (action.type) {
    case UPDATE_FORM_FIELD:
      return {
        ...state,
        fields: { ...state.fields, [action.payload.field]: action.payload.value },
        error: null,
      };
    case RESET_FORM:
      return initialState;
    case FORM_ERROR:
      return { ...state, error: action.payload };
    default:
      return state;
  }
};

export default formReducer;
