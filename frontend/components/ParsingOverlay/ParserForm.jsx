import React, { useState, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { startParsing } from '../../actions/parsingActions';
import socket from '../../utils/socket';

const ParserForm = () => {
  const [emailContent, setEmailContent] = useState('');
  const [documentImage, setDocumentImage] = useState(null);
  const [parserOption, setParserOption] = useState('enhanced_parser');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const dispatch = useDispatch();

  useEffect(() => {
    // Set up socket event listeners
    socket.on('connect', () => {
      console.log('Socket connected:', socket.id);
    });

    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      dispatch({
        type: 'SET_ERROR',
        payload: 'Connection error. Please refresh and try again.',
      });
    });

    socket.on('parsing_started', handleParsingStarted);
    socket.on('parsing_progress', handleParsingProgress);
    socket.on('parsing_completed', handleParsingCompleted);
    socket.on('parsing_error', handleParsingError);

    // Cleanup on unmount
    return () => {
      socket.off('parsing_started', handleParsingStarted);
      socket.off('parsing_progress', handleParsingProgress);
      socket.off('parsing_completed', handleParsingCompleted);
      socket.off('parsing_error', handleParsingError);
    };
  }, [dispatch]);

  const validateForm = () => {
    if (!emailContent.trim() && !documentImage) {
      dispatch({
        type: 'SET_ERROR',
        payload: 'Please provide either email content or a document image.',
      });
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;

    if (!validateForm()) return;

    if (!socket.connected) {
      dispatch({
        type: 'SET_ERROR',
        payload: 'No connection to server. Please refresh and try again.',
      });
      return;
    }

    try {
      setIsSubmitting(true);

      const formData = new FormData();
      formData.append('parser_option', parserOption);
      if (emailContent.trim()) {
        formData.append('email_content', emailContent.trim());
      }
      if (documentImage) {
        formData.append('document_image', documentImage);
      }
      formData.append('socket_id', socket.id);

      dispatch(startParsing(formData));

    } catch (error) {
      console.error('Error submitting form:', error);
      dispatch({
        type: 'SET_ERROR',
        payload: 'Failed to start parsing. Please try again.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleParsingStarted = () => {
    dispatch({ type: 'START_PARSING' });
    dispatch({
      type: 'ADD_TOAST',
      payload: {
        id: Date.now(),
        type: 'info',
        message: 'Parsing started...',
      },
    });
  };

  const handleParsingProgress = (data) => {
    dispatch({
      type: 'UPDATE_PROGRESS',
      payload: data,
    });
  };

  const handleParsingCompleted = (result) => {
    setIsSubmitting(false);
    dispatch({
      type: 'COMPLETE_PARSING',
      payload: result,
    });
    dispatch({
      type: 'ADD_TOAST',
      payload: {
        id: Date.now(),
        type: 'success',
        message: 'Parsing completed successfully!',
      },
    });
  };

  const handleParsingError = (error) => {
    setIsSubmitting(false);
    console.error('Parsing error:', error);
    dispatch({
      type: 'SET_ERROR',
      payload: error.error || 'An error occurred during parsing.',
    });
    dispatch({
      type: 'ADD_TOAST',
      payload: {
        id: Date.now(),
        type: 'error',
        message: error.error || 'Parsing failed. Please try again.',
      },
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md">
      <div className="space-y-6">
        {/* Email Content Input */}
        <div>
          <label htmlFor="email_content" className="block text-sm font-medium text-gray-700">
            Email Content
          </label>
          <div className="mt-1">
            <textarea
              id="email_content"
              name="email_content"
              rows={6}
              value={emailContent}
              onChange={(e) => setEmailContent(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="Paste your email content here..."
            />
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Paste the email content you want to parse
          </p>
        </div>

        {/* Document Image Upload */}
        <div>
          <label htmlFor="document_image" className="block text-sm font-medium text-gray-700">
            Document Image
          </label>
          <div className="mt-1">
            <input
              id="document_image"
              name="document_image"
              type="file"
              accept="image/*"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  if (file.size > 5 * 1024 * 1024) {
                    dispatch({
                      type: 'SET_ERROR',
                      payload: 'File size must be less than 5MB',
                    });
                    return;
                  }
                  setDocumentImage(file);
                }
              }}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Upload a document image (JPG, PNG, max 5MB)
          </p>
        </div>

        {/* Parser Option Selection */}
        <div>
          <label htmlFor="parser_option" className="block text-sm font-medium text-gray-700">
            Parser Option
          </label>
          <div className="mt-1">
            <select
              id="parser_option"
              name="parser_option"
              value={parserOption}
              onChange={(e) => setParserOption(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="enhanced_parser">Enhanced Parser</option>
            </select>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Select the parsing method to use
          </p>
        </div>

        {/* Submit Button */}
        <div>
          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
              isSubmitting
                ? 'bg-blue-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
            }`}
          >
            {isSubmitting ? 'Processing...' : 'Start Parsing'}
          </button>
        </div>
      </div>
    </form>
  );
};

export default ParserForm;