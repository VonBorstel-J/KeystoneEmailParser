// frontend/actions/api.js
import axios from 'axios';

/**
 * Initiates the parsing of an email by sending data to the backend.
 * @param {Object} data - The data to send for parsing.
 * @returns {Promise<Object>} - The response from the backend.
 */
export const parseEmail = async (data) => {
  try {
    const formData = new FormData();
    
    if (data.email_content) formData.append('email_content', data.email_content);
    if (data.document_image) formData.append('document_image', data.document_image);
    formData.append('parser_option', data.parser_option);
    formData.append('socket_id', data.socket_id);

    const response = await axios.post('/api/parse_email', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  } catch (error) {
    console.error('Error occurred during email parsing request:', error);

    if (error.response) {
      // Server responded with a status code outside of 2xx range
      return {
        success: false,
        message: `Parsing failed: ${error.response.data?.message || 'Unknown server error'}`,
        status: error.response.status,
      };
    } else if (error.request) {
      // Request was made but no response was received
      return {
        success: false,
        message: 'No response received from the server. Please check your network connection.',
      };
    } else {
      // Something else happened while setting up the request
      return {
        success: false,
        message: `Request setup error: ${error.message}`,
      };
    }
  }
};

/**
 * Checks the health of the backend API.
 * @returns {Promise<Object>} - The health status.
 */
export const checkHealth = async () => {
  try {
    const response = await axios.get('/api/health');
    return response.data;
  } catch (error) {
    console.error('Error occurred during health check request:', error);

    if (error.response) {
      return {
        success: false,
        message: `Health check failed: ${error.response.data?.message || 'Unknown server error'}`,
        status: error.response.status,
      };
    } else if (error.request) {
      return {
        success: false,
        message: 'No response received from the server during health check. Please check your network connection.',
      };
    } else {
      return {
        success: false,
        message: `Health check request error: ${error.message}`,
      };
    }
  }
};
