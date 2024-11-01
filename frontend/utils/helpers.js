// frontend/utils/helpers.js
import { v4 as uuidv4 } from 'uuid';

/**
 * Generates a unique identifier.
 * @returns {string} - A UUID.
 */
export const generateId = () => {
  try {
    return uuidv4();
  } catch (error) {
    console.error('Error generating UUID:', error);
    return null; // Return null if there's an error
  }
};

/**
 * Formats data into JSON or human-readable string.
 * @param {Object} data - The data to format.
 * @param {string} format - 'json' or 'human'.
 * @returns {string} - Formatted string.
 */
export const formatData = (data, format) => {
  try {
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid data provided for formatting');
    }

    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    }

    if (format === 'human') {
      // Formatting the data into a human-readable string
      return Object.entries(data)
        .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value, null, 2) : value}`)
        .join('\n');
    }

    throw new Error(`Unknown format: ${format}`);
  } catch (error) {
    console.error('Error formatting data:', error);
    return 'Formatting error: Unable to format data.';
  }
};
