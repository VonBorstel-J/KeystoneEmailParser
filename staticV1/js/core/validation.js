// static/js/core/validation.js

class ValidationManager {
  constructor() {
    this.rules = {
      emailContent: [
        {
          test: (value) => typeof value === 'string' && value.trim().length > 0,
          message: 'Email content is required',
        },
        {
          test: (value) => typeof value === 'string' && value.length <= 50000,
          message: 'Email content too long',
        },
      ],
      parserOption: [
        {
          test: (value) => value !== '',
          message: 'Please select a parser option.',
        },
      ],
      documentImage: [
        {
          test: (file) => {
            if (!file) return true; // Optional field
            const validTypes = ['image/png', 'image/jpeg', 'image/gif'];
            return validTypes.includes(file.type);
          },
          message: 'Invalid file type.',
        },
        {
          test: (file) => {
            if (!file) return true; // Optional field
            return file.size <= 10 * 1024 * 1024;
          },
          message: 'File size exceeds 10MB.',
        },
      ],
    };
  }

  initialize() {
    // Any initialization logic here
    console.log('Validation Manager initialized');
    return this;
  }

  validate(field, value) {
    const fieldRules = this.rules[field];
    if (!fieldRules) return [];
    return fieldRules.reduce((errors, rule) => {
      if (!rule.test(value)) {
        errors.push(rule.message);
      }
      return errors;
    }, []);
  }

  static getInstance() {
    if (!ValidationManager.instance) {
      ValidationManager.instance = new ValidationManager();
    }
    return ValidationManager.instance;
  }
}

// Create and export a singleton instance
const validationManager = ValidationManager.getInstance();

export const validateEmailContent = (content) => {
  const errors = validationManager.validate('emailContent', content);
  return errors.length > 0 ? errors[0] : null;
};


export { validationManager as default };