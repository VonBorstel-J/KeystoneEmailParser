// static/js/actions/formActions.js
import { LOAD_SAMPLE_EMAIL, SET_FORM_ERRORS, CLEAR_FORM_ERRORS } from './actionTypes.js';
import { showToast } from './toastActions.js';

const EMAIL_TEMPLATES = {
  claim: `Dear Sir/Madam,

I am writing to formally file a claim regarding...`,
  informal_claim: `Hi there,

I need to file a claim because...`,
  formal_fire_claim: `To Whom It May Concern,

I regret to inform you that...`,
};

export const loadSampleEmail = (templateName) => ({
  type: LOAD_SAMPLE_EMAIL,
  payload: templateName,
});

export const setFormErrors = (errors) => ({
  type: SET_FORM_ERRORS,
  payload: errors,
});

export const clearFormErrors = () => ({
  type: CLEAR_FORM_ERRORS,
});

// Thunk Action for loading sample email
export const fetchSampleEmail = (templateName) => (dispatch) => {
  if (EMAIL_TEMPLATES[templateName]) {
    dispatch(loadSampleEmail(templateName));
    dispatch(showToast('success', 'Sample email loaded.'));
  } else {
    dispatch(showToast('error', 'Invalid email template.'));
  }
};
