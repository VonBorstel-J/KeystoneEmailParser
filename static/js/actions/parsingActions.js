// static/js/actions/parsingActions.js

import {
    START_PARSING,
    UPDATE_PARSING_PROGRESS,
    PARSING_COMPLETE,
    PARSING_ERROR,
  } from './actionTypes';
  
  // Action to start parsing
  export const startParsing = () => ({
    type: START_PARSING,
  });
  
  // Action to update parsing progress
  export const updateParsingProgress = (progress) => ({
    type: UPDATE_PARSING_PROGRESS,
    payload: progress,
  });
  
  // Action when parsing is complete
  export const parsingComplete = () => ({
    type: PARSING_COMPLETE,
  });
  
  // Action to handle parsing errors
  export const parsingError = (error) => ({
    type: PARSING_ERROR,
    payload: error,
  });
  