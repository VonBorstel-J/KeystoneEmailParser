// static/js/ui/toast.js

import React from 'react';

/**
 * Toast Notification Component
 * @param {Object} props 
 * @param {'success' | 'error'} props.type
 * @param {string} props.message
 * @param {Function} props.onClose
 */
const Toast = ({ type, message, onClose }) => {
  const bgColor = type === 'success' ? 'bg-green-100' : 'bg-red-100';
  const borderColor = type === 'success' ? 'border-green-500' : 'border-red-500';
  const textColor = type === 'success' ? 'text-green-700' : 'text-red-700';
  const icon = type === 'success' ? (
    <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
    </svg>
  ) : (
    <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );

  return (
    <div className={`flex items-center ${bgColor} border-l-4 ${borderColor} ${textColor} p-4 rounded-md shadow-lg`} role="alert">
      <div className="flex-shrink-0">
        {icon}
      </div>
      <div className="ml-3">
        <p className="text-sm">{message}</p>
      </div>
      <button onClick={onClose} className="ml-auto bg-transparent border-0 text-current hover:text-gray-700">
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
};

export default Toast;
