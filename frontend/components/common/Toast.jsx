// frontend/components/common/Toast.jsx
import React from 'react';

/**
 * Toast component displays a single notification message.
 * @param {Object} props - Properties passed to the component.
 * @param {string} props.message - The message to display.
 * @param {string} props.type - Type of the toast (e.g., success, error).
 * @param {Function} props.onClose - Callback function to handle toast close.
 */
const Toast = ({ message, type, onClose }) => {
  const bgColor = type === 'error' ? 'bg-red-500' : 'bg-green-500';

  return (
    <div
      className={`fixed bottom-4 right-4 p-4 rounded shadow text-white flex items-start ${bgColor}`}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <div className="flex-1">
        {message}
      </div>
      <button
        onClick={onClose}
        className="ml-4 bg-transparent border-none text-white font-bold"
        aria-label="Close notification"
      >
        &times;
      </button>
    </div>
  );
};

export default Toast;
