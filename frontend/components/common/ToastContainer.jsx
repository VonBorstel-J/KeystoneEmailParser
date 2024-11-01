// frontend/components/common/ToastContainer.jsx
import React from 'react';
import { useSelector } from 'react-redux';
import Toast from './Toast';

/**
 * ToastContainer displays a list of toast notifications.
 */
const ToastContainer = () => {
  const toasts = useSelector((state) => state.parsing.toasts);

  return (
    <div>
      {toasts.map((toast) => (
        <Toast key={toast.id} message={toast.message} type={toast.type} />
      ))}
    </div>
  );
};

export default ToastContainer;
