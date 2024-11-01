import React, { useState, useEffect, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { startParsing } from '../../actions/parsingActions';
import socketManager from '../../utils/socket';

const ParserForm = () => {
  const [emailContent, setEmailContent] = useState('');
  const [documentImage, setDocumentImage] = useState(null);
  const [parserOption, setParserOption] = useState('enhanced_parser');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const dispatch = useDispatch();

  const handleParsingStarted = useCallback(() => {
    dispatch({ type: 'START_PARSING' });
    dispatch({
      type: 'ADD_TOAST',
      payload: {
        id: Date.now(),
        type: 'info',
        message: 'Parsing started...',
      },
    });
  }, [dispatch]);

  const handleParsingProgress = useCallback((data) => {
    dispatch({
      type: 'UPDATE_PROGRESS',
      payload: data,
    });
  }, [dispatch]);

  const handleParsingCompleted = useCallback((result) => {
    setIsSubmitting(false);
    setUploadProgress(0);
    dispatch({
      type: 'COMPLETE_PARSING',
      payload: result.result,
    });
    dispatch({
      type: 'ADD_TOAST',
      payload: {
        id: Date.now(),
        type: 'success',
        message: 'Parsing completed successfully!',
      },
    });
  }, [dispatch]);

  const handleParsingError = useCallback((error) => {
    setIsSubmitting(false);
    setUploadProgress(0);
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
  }, [dispatch]);

  useEffect(() => {
    socketManager.on('parsing_started', handleParsingStarted);
    socketManager.on('parsing_progress', handleParsingProgress);
    socketManager.on('parsing_completed', handleParsingCompleted);
    socketManager.on('parsing_error', handleParsingError);

    return () => {
      socketManager.off('parsing_started', handleParsingStarted);
      socketManager.off('parsing_progress', handleParsingProgress);
      socketManager.off('parsing_completed', handleParsingCompleted);
      socketManager.off('parsing_error', handleParsingError);
    };
  }, [handleParsingStarted, handleParsingProgress, handleParsingCompleted, handleParsingError]);

  const validateForm = useCallback(() => {
    if (!emailContent.trim() && !documentImage) {
      dispatch({
        type: 'SET_ERROR',
        payload: 'Please provide either email content or a document image.',
      });
      return false;
    }
    return true;
  }, [emailContent, documentImage, dispatch]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;
  
    // Debug log
    console.log('Form submission started');
    console.log('Email content:', emailContent);
    console.log('Document image:', documentImage);
    console.log('Parser option:', parserOption);
    console.log('Socket ID:', socketManager.getId());
  
    if (!validateForm()) {
      console.log('Form validation failed');
      return;
    }
  
    if (!socketManager.isConnected()) {
      console.log('Socket not connected');
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
        console.log('Added email content to form data');
      }
      
      if (documentImage) {
        formData.append('document_image', documentImage);
        console.log('Added document image to form data');
      }
      
      formData.append('socket_id', socketManager.getId());
      console.log('Added socket ID to form data:', socketManager.getId());
  
      // Log the full form data
      for (let pair of formData.entries()) {
        console.log('Form data entry:', pair[0], pair[1]);
      }
  
      await dispatch(startParsing(formData));
      console.log('Parsing started successfully');
  
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

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        dispatch({
          type: 'SET_ERROR',
          payload: 'File size must be less than 5MB',
        });
        return;
      }
      if (!file.type.startsWith('image/')) {
        dispatch({
          type: 'SET_ERROR',
          payload: 'Please upload a valid image file',
        });
        return;
      }
      setDocumentImage(file);
    }
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
              disabled={isSubmitting}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
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
              onChange={handleFileChange}
              disabled={isSubmitting}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Upload a document image (JPG, PNG, max 5MB)
          </p>
          {uploadProgress > 0 && uploadProgress < 100 && (
            <div className="mt-2">
              <div className="h-2 bg-gray-200 rounded-full">
                <div
                  className="h-2 bg-blue-500 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
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
              disabled={isSubmitting}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
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
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white transition-colors duration-200 ${
              isSubmitting
                ? 'bg-blue-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
            }`}
          >
            {isSubmitting ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </span>
            ) : 'Start Parsing'}
          </button>
        </div>
      </div>
    </form>
  );
};

export default ParserForm;