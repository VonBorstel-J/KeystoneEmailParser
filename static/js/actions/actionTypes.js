// static/js/actions/actionTypes.js
// Theme Actions
export const TOGGLE_THEME = 'TOGGLE_THEME';
export const SET_THEME = 'SET_THEME';

// Modal Actions  
export const OPEN_MODAL = 'OPEN_MODAL';
export const CLOSE_MODAL = 'CLOSE_MODAL';

// Toast Actions
export const ADD_TOAST = 'ADD_TOAST';
export const REMOVE_TOAST = 'REMOVE_TOAST';

// Upload Actions
export const UPLOAD_START = 'UPLOAD_START';
export const UPLOAD_PROGRESS = 'UPLOAD_PROGRESS';
export const UPLOAD_COMPLETE = 'UPLOAD_COMPLETE';
export const UPLOAD_ERROR = 'UPLOAD_ERROR';

// Socket Actions
export const SET_SOCKET_CONNECTED = 'SET_SOCKET_CONNECTED';
export const SET_SOCKET_DISCONNECTED = 'SET_SOCKET_DISCONNECTED'; 
export const SET_SOCKET_ERROR = 'SET_SOCKET_ERROR';

// Parsing Actions
export const START_PARSING = 'START_PARSING';
export const UPDATE_PARSING_PROGRESS = 'UPDATE_PARSING_PROGRESS';
export const PARSING_SUCCESS = 'PARSING_SUCCESS';
export const PARSING_FAILURE = 'PARSING_FAILURE';

// Form Actions
export const LOAD_SAMPLE_EMAIL = 'LOAD_SAMPLE_EMAIL';
export const SET_FORM_ERRORS = 'SET_FORM_ERRORS';
export const CLEAR_FORM_ERRORS = 'CLEAR_FORM_ERRORS';


export const PARSE_EMAIL_INITIATED = 'PARSE_EMAIL_INITIATED';
export const PARSE_EMAIL_SUCCESS = 'PARSE_EMAIL_SUCCESS';
export const PARSE_EMAIL_FAILURE = 'PARSE_EMAIL_FAILURE';
export const INCREMENT_RETRY = 'INCREMENT_RETRY';
export const RESET_RETRY = 'RESET_RETRY';
export const SHOW_TOAST = 'SHOW_TOAST';
