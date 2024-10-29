// static/js/actions/uploadActions.js

import {
    UPLOAD_START,
    UPLOAD_PROGRESS,
    UPLOAD_COMPLETE,
    UPLOAD_ERROR,
  } from './actionTypes';
  
  // Action to start upload
  export const uploadStart = () => ({
    type: UPLOAD_START,
  });
  
  // Action to update upload progress
  export const uploadProgress = (progress) => ({
    type: UPLOAD_PROGRESS,
    payload: progress,
  });
  
  // Action when upload is complete
  export const uploadComplete = () => ({
    type: UPLOAD_COMPLETE,
  });
  
  // Action to handle upload errors
  export const uploadError = (error) => ({
    type: UPLOAD_ERROR,
    payload: error,
  });
  