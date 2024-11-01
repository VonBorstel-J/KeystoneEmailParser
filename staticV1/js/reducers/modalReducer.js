// static/js/reducers/modalReducer.js
import { OPEN_MODAL, CLOSE_MODAL } from '@actions/actionTypes.js';

const initialState = {
  isOpen: false,
  modalType: null,
};

const modalReducer = (state = initialState, action) => {
  switch (action.type) {
    case OPEN_MODAL:
      return {
        isOpen: true,
        modalType: action.payload,
      };
    case CLOSE_MODAL:
      return {
        isOpen: false,
        modalType: null,
      };
    default:
      return state;
  }
};

export default modalReducer;
