// static/js/actions/toastActions.js

import { ADD_TOAST, REMOVE_TOAST } from './actionTypes';
import { v4 as uuidv4 } from 'uuid';

export const addToast = (type, message, duration) => ({
  type: ADD_TOAST,
  payload: {
    id: uuidv4(),
    type,
    message,
    duration,
  },
});

export const removeToast = (id) => ({
  type: REMOVE_TOAST,
  payload: id,
});
