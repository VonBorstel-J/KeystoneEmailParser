// frontend/core/validation.js

/**
 * Validates the parser form inputs.
 * @param {Object} inputs - The form inputs.
 * @returns {Object} - Validation result with isValid flag and message.
 */
export const validateForm = (inputs) => {
  const { parser_option, email_content, document_image } = inputs;

  // Validate parser_option
  if (!parser_option) {
    return { isValid: false, message: 'Please select a parser option.' };
  }

  // Validate email_content or document_image presence
  if (!email_content && !document_image) {
    return { isValid: false, message: 'Please provide email content or a document image.' };
  }

  // Validate email_content type and length
  if (email_content) {
    if (typeof email_content !== 'string') {
      return { isValid: false, message: 'Email content must be a valid text string.' };
    }
    if (email_content.trim().length === 0) {
      return { isValid: false, message: 'Email content cannot be empty.' };
    }
    if (email_content.trim().length > 5000) {
      return { isValid: false, message: 'Email content is too long. Please limit it to 5000 characters.' };
    }
  }

  // Validate document_image type and size
  if (document_image) {
    if (!(document_image instanceof File)) {
      return { isValid: false, message: 'Document image must be a valid file.' };
    }

    const validImageTypes = ['image/jpeg', 'image/png'];
    if (!validImageTypes.includes(document_image.type)) {
      return { isValid: false, message: 'Invalid image type. Please upload a JPEG or PNG image.' };
    }

    const maxSizeInBytes = 5 * 1024 * 1024; // 5MB
    if (document_image.size > maxSizeInBytes) {
      return { isValid: false, message: 'Document image size should not exceed 5MB.' };
    }
  }

  // If all validations pass
  return { isValid: true, message: '' };
};
