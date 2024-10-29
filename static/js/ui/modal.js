// static/js/ui/modal.js

import React from 'react';

/**
 * Modal Component
 * @param {Object} props 
 * @param {boolean} props.isOpen
 * @param {string} props.title
 * @param {React.ReactNode} props.children
 * @param {Function} props.onClose
 */
const Modal = ({ isOpen, title, children, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
      <div className="bg-white rounded-lg max-w-2xl w-full mx-4">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 id="modalTitle" className="text-lg font-medium text-gray-900">{title}</h3>
        </div>
        <div className="px-6 py-4">
          {children}
        </div>
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
          <button onClick={onClose} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200" aria-label="Close Modal">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default Modal;
