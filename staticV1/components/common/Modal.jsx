// static/components/common/Modal.jsx
import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import FocusLock from 'react-focus-lock';
import { Transition } from '@headlessui/react';

const Modal = ({ isOpen, onClose, title, children }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      // Prevent background scrolling when modal is open
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'auto';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <Transition appear show={isOpen} as={React.Fragment}>
      <div
        className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <FocusLock>
          <Transition.Child
            as={React.Fragment}
            enter="transform transition duration-300"
            enterFrom="scale-95 opacity-0"
            enterTo="scale-100 opacity-100"
            leave="transform transition duration-200"
            leaveFrom="scale-100 opacity-100"
            leaveTo="scale-95 opacity-0"
          >
            <div className="bg-white dark:bg-gray-800 rounded-lg max-w-lg w-full mx-4 p-6 relative">
              {/* Close Button */}
              <button
                onClick={onClose}
                className="absolute top-4 right-4 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100"
                aria-label="Close Modal"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

              {/* Modal Title */}
              <h3 id="modal-title" className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                {title}
              </h3>

              {/* Modal Content */}
              <div className="modal-content">
                {children}
              </div>
            </div>
          </Transition.Child>
        </FocusLock>
      </div>
    </Transition>
  );
};

Modal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
};

export default Modal;
