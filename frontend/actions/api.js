import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Accept': 'application/json'
  }
});

export const parseEmail = async (data) => {
  try {
    const formData = new FormData();
    
    if (data.email_content) {
      formData.append('email_content', data.email_content);
    }
    if (data.document_image) {
      formData.append('document_image', data.document_image);
    }
    formData.append('parser_option', data.parser_option);
    formData.append('socket_id', data.socket_id);

    // Log the form data for debugging
    for (let pair of formData.entries()) {
      console.log(pair[0] + ': ' + pair[1]);
    }

    const response = await api.post('/parse_email', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    return response.data;
  } catch (error) {
    console.error('Error occurred during email parsing request:', error);
    
    if (error.response) {
      console.error('Error response:', error.response.data);
      throw new Error(error.response.data.error_message || 'Server error occurred');
    } else if (error.request) {
      throw new Error('No response received from server');
    } else {
      throw new Error(`Request failed: ${error.message}`);
    }
  }
};

export const checkHealth = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
};