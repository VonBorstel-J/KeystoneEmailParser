// static/components/common/ToastContainer.jsx
import React from 'react';
import { useSelector } from 'react-redux';
import Toast from './Toast.jsx';

const ToastContainer = () => {
  const toasts = useSelector((state) => state.toast.toasts);

  return (
    <div id="toast-container" className="fixed top-4 right-4 flex flex-col items-end space-y-2 z-50">
      {toasts.map((toast) => (
        <Toast key={toast.id} id={toast.id} type={toast.type} message={toast.message} />
      ))}
    </div>
  );
};

export default ToastContainer;
