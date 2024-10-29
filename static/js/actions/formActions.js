// static/js/actions/formActions.js

import { UPDATE_FORM_FIELD, RESET_FORM, FORM_ERROR } from './actionTypes';

// Action to update a form field
export const updateFormField = (field, value) => ({
  type: UPDATE_FORM_FIELD,
  payload: { field, value },
});

// Action to reset the form
export const resetForm = () => ({
  type: RESET_FORM,
});

// Action to handle form errors
export const formError = (error) => ({
  type: FORM_ERROR,
  payload: error,
});
