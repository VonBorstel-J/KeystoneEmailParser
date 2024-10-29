// static/js/core/parser.js
class Parser {
  constructor(socket) {
    this.socket = socket;
  }

  async parseEmail(formData) {
    try {
      const response = await fetch('/parse_email', {
        method: 'POST',
        body: formData,
      });
      const contentType = response.headers.get('Content-Type');
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error_message || 'An error occurred while parsing.');
        }
        return data;
      } else {
        throw new Error('Unexpected response format.');
      }
    } catch (error) {
      console.error('parseEmail error:', error);
      throw error;
    }
  }
}

export default Parser;
