// static/components/common/ToastContainer.jsx

import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import Toast from './Toast';
import { removeToast } from '../../actions/toastActions';

const ToastContainer = () => {
  const toasts = useSelector((state) => state.toasts);
  const dispatch = useDispatch();

  const handleClose = (id) => {
    dispatch(removeToast(id));
  };

  return (
    <div className="fixed top-5 right-5 flex flex-col space-y-2 z-50">
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onClose={handleClose} />
      ))}
    </div>
  );
};

export default ToastContainer;
