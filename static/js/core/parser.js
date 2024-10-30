// static/js/core/parser.js
import store from '../store.js';
import { showToast } from '../actions/toastActions.js';
import { startParsing, parsingSuccess, parsingFailure } from '../actions/parsingActions.js';

class Parser {
  constructor(socket) {
    this.socket = socket;
  }

  parseEmail({ emailContent, documentImage, parserOption }) {
    store.dispatch(startParsing());

    const formData = new FormData();
    formData.append('email_content', emailContent);
    formData.append('parser_option', parserOption);
    if (documentImage) {
      formData.append('document_image', documentImage);
    }
    formData.append('socket_id', this.socket.id);

    return fetch('/api/parse', {
      method: 'POST',
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          store.dispatch(parsingSuccess(data.results));
          store.dispatch(showToast('success', 'Parsing completed successfully.'));
        } else {
          throw new Error(data.error_message || 'Parsing failed.');
        }
      })
      .catch((error) => {
        store.dispatch(parsingFailure(error.message));
        store.dispatch(showToast('error', error.message));
        throw error;
      });
  }
}

export default Parser;
