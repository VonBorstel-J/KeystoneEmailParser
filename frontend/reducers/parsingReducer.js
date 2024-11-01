// frontend/reducers/parsingReducer.js
const initialState = {
  parsingProgress: null, // { stage: string, percentage: number }
  parsingResult: null, // Parsed data
  error: null, // Error messages
  toasts: [], // Array of toast notifications
};

/**
 * Parsing reducer handles actions related to parsing progress and results.
 * @param {Object} state - Current state.
 * @param {Object} action - Dispatched action.
 * @returns {Object} - New state.
 */
const parsingReducer = (state = initialState, action) => {
  switch (action.type) {
    case 'START_PARSING':
      return {
        ...state,
        parsingProgress: { stage: 'Starting', percentage: 0 },
        parsingResult: null,
        error: null,
      };
      
    case 'UPDATE_PROGRESS':
      if (action.payload && action.payload.percentage >= 0 && action.payload.percentage <= 100) {
        return {
          ...state,
          parsingProgress: {
            stage: action.payload.stage || 'In Progress',
            percentage: action.payload.percentage,
          },
        };
      } else {
        console.error('Invalid progress update received:', action.payload);
        return {
          ...state,
          error: 'Received an invalid progress update.',
        };
      }

    case 'COMPLETE_PARSING':
      if (action.payload) {
        return {
          ...state,
          parsingProgress: null,
          parsingResult: action.payload,
        };
      } else {
        console.error('Invalid parsing result received:', action.payload);
        return {
          ...state,
          error: 'Failed to complete parsing. Invalid data received.',
        };
      }

    case 'SET_ERROR':
      return {
        ...state,
        parsingProgress: null,
        parsingResult: null, // Clear any previous results on error
        error: action.payload || 'An unknown error occurred.',
      };

    case 'ADD_TOAST':
      if (action.payload && !state.toasts.some((toast) => toast.id === action.payload.id)) {
        return {
          ...state,
          toasts: [...state.toasts, action.payload],
        };
      } else {
        console.warn('Attempted to add a duplicate or invalid toast:', action.payload);
        return state;
      }

    case 'REMOVE_TOAST':
      return {
        ...state,
        toasts: state.toasts.filter((toast) => toast.id !== action.payload),
      };

    default:
      return state;
  }
};

export default parsingReducer;
