// static/js/reducers/formReducer.js
import { LOAD_SAMPLE_EMAIL, SET_FORM_ERRORS, CLEAR_FORM_ERRORS } from '@actions/actionTypes.js';

const EMAIL_TEMPLATES = {
  claim: `Dear Sir/Madam,

I am writing to formally file a claim regarding...`,
  informal_claim: `Hi there,

I need to file a claim because...`,
  formal_fire_claim: `To Whom It May Concern,

I regret to inform you that...`,
};

const initialState = {
  email_content: '',
  parser_option: '',
  errors: {},
  isSubmitting: false,
};

const formReducer = (state = initialState, action) => {
  switch (action.type) {
    case LOAD_SAMPLE_EMAIL:
      return {
        ...state,
        email_content: EMAIL_TEMPLATES[action.payload] || '',
        errors: {},
      };
    case SET_FORM_ERRORS:
      return {
        ...state,
        errors: action.payload,
      };
    case CLEAR_FORM_ERRORS:
      return {
        ...state,
        errors: {},
      };
    default:
      return state;
  }
};

export default formReducer;
