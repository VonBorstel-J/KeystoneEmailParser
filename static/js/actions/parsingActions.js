// static/js/actions/parsingActions.js
import {
  START_PARSING,
  UPDATE_PARSING_PROGRESS,
  PARSING_SUCCESS,
  PARSING_FAILURE,
} from './actionTypes.js';
import { showToast } from './toastActions.js';

export const startParsing = () => ({
  type: START_PARSING,
});

export const updateParsingProgress = (progress) => ({
  type: UPDATE_PARSING_PROGRESS,
  payload: progress,
});

export const parsingSuccess = (results) => ({
  type: PARSING_SUCCESS,
  payload: results,
});

export const parsingFailure = (error) => ({
  type: PARSING_FAILURE,
  payload: error,
});

// Thunk Action for parsing email
export const parseEmail = ({ emailContent, documentImage, parserOption }) => (dispatch, getState) => {
  dispatch(startParsing());

  const socket = getState().socket.socketInstance; // Assuming socket instance is stored here
  const formData = new FormData();
  formData.append('email_content', emailContent);
  formData.append('parser_option', parserOption);
  if (documentImage) {
    formData.append('document_image', documentImage);
  }
  formData.append('socket_id', socket.id);

  fetch('/api/parse', {
    method: 'POST',
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        dispatch(parsingSuccess(data.results));
        dispatch(showToast('success', 'Parsing completed successfully.'));
      } else {
        throw new Error(data.error_message || 'Parsing failed.');
      }
    })
    .catch((error) => {
      dispatch(parsingFailure(error.message));
      dispatch(showToast('error', error.message));
    });
};
