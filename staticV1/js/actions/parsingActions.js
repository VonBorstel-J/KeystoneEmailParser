// static/js/actions/parsingActions.js
import axios from 'axios';

// Action Types
export const PARSE_EMAIL_INITIATED = 'PARSE_EMAIL_INITIATED';
export const PARSE_EMAIL_SUCCESS = 'PARSE_EMAIL_SUCCESS';
export const PARSE_EMAIL_FAILURE = 'PARSE_EMAIL_FAILURE';

// Action Creators
export const parseEmail = (formData, socket) => async (dispatch) => {
  dispatch({ type: PARSE_EMAIL_INITIATED });

  try {
    const { emailContent, parserOption } = formData;

    const data = new FormData();
    data.append('email_content', emailContent);
    data.append('parser_option', parserOption);
    data.append('socket_id', socket.id);

    const response = await axios.post('/parse_email', data);

    // Assuming the API responds with a status indicating success
    if (response.status === 202) {
      // Parsing started, no further action needed here
      // Success will be handled via socket events
      return;
    }

    // If the API responds with immediate success
    dispatch({
      type: PARSE_EMAIL_SUCCESS,
      payload: response.data.result,
    });
  } catch (error) {
    const errorMessage =
      error.response?.data?.error_message || error.message || 'Parsing failed.';
    dispatch({
      type: PARSE_EMAIL_FAILURE,
      payload: errorMessage,
    });
  }
};

export const parsingCompleted = (result) => ({
  type: PARSE_EMAIL_SUCCESS,
  payload: result,
});

export const parsingError = (error) => ({
  type: PARSE_EMAIL_FAILURE,
  payload: error,
});
