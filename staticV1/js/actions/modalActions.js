// static/js/actions/modalActions.js
import { OPEN_MODAL, CLOSE_MODAL } from './actionTypes.js';

export const openModal = (modalType) => ({
  type: OPEN_MODAL,
  payload: modalType,
});

export const closeModal = () => ({
  type: CLOSE_MODAL,
});
