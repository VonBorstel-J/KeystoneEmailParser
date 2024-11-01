// static/js/actions/toastActions.js
import { ADD_TOAST, REMOVE_TOAST } from './actionTypes.js';
import { v4 as uuidv4 } from 'uuid';

export const addToast = (toast) => ({
  type: ADD_TOAST,
  payload: { id: uuidv4(), ...toast },
});

export const removeToast = (id) => ({
  type: REMOVE_TOAST,
  payload: id,
});

// Convenience action creators
export const showToast = (type, message) => (dispatch) => {
  dispatch(addToast({ type, message }));
};
