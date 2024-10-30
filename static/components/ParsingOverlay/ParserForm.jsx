// static/components/ParsingOverlay/ParserForm.jsx
import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { parseEmail } from '@actions/parsingActions';
import { setFormErrors, clearFormErrors } from '@actions/formActions';
import ValidationManager from '@core/validation';

const ParserForm = () => {
  const dispatch = useDispatch();
  const { isSubmitting, errors } = useSelector(state => state.form);
  const [formData, setFormData] = useState({
    emailContent: '',
    parserOption: '',
    documentImage: null
  });

  const handleInputChange = (e) => {
    const { name, value, files } = e.target;
    if (files) {
      setFormData(prev => ({
        ...prev,
        [name]: files[0]
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    Object.keys(formData).forEach(field => {
      const fieldErrors = ValidationManager.validate(field, formData[field]);
      if (fieldErrors.length > 0) {
        newErrors[field] = fieldErrors;
      }
    });

    if (Object.keys(newErrors).length > 0) {
      dispatch(setFormErrors(newErrors));
      return false;
    }
    
    dispatch(clearFormErrors());
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    const formDataToSend = new FormData();
    formDataToSend.append('emailContent', formData.emailContent);
    formDataToSend.append('parserOption', formData.parserOption);
    if (formData.documentImage) {
      formDataToSend.append('documentImage', formData.documentImage);
    }

    dispatch(parseEmail(formDataToSend));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6" encType="multipart/form-data">
      <div>
        <label htmlFor="emailContent" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
          Email Content
        </label>
        <textarea
          id="emailContent"
          name="emailContent"
          value={formData.emailContent}
          onChange={handleInputChange}
          className={`mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
            errors.emailContent ? 'border-red-500' : ''
          }`}
          rows={10}
        />
        {errors.emailContent && (
          <p className="mt-1 text-sm text-red-600">{errors.emailContent[0]}</p>
        )}
      </div>

      <div>
        <label htmlFor="parserOption" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
          Parser Option
        </label>
        <select
          id="parserOption"
          name="parserOption"
          value={formData.parserOption}
          onChange={handleInputChange}
          className={`mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
            errors.parserOption ? 'border-red-500' : ''
          }`}
        >
          <option value="">Select a parser</option>
          <option value="enhanced">Enhanced Parser</option>
          <option value="composite">Composite Parser</option>
        </select>
        {errors.parserOption && (
          <p className="mt-1 text-sm text-red-600">{errors.parserOption[0]}</p>
        )}
      </div>

      <div>
        <label htmlFor="documentImage" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
          Document Image (Optional)
        </label>
        <input
          type="file"
          id="documentImage"
          name="documentImage"
          onChange={handleInputChange}
          accept="image/*"
          className={`mt-1 block w-full ${
            errors.documentImage ? 'border-red-500' : ''
          }`}
        />
        {errors.documentImage && (
          <p className="mt-1 text-sm text-red-600">{errors.documentImage[0]}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        {isSubmitting ? 'Parsing...' : 'Parse Email'}
      </button>
    </form>
  );
};

export default ParserForm;