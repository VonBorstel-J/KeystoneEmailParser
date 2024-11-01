// frontend/components/ParsingOverlay/ProgressBar.jsx
import React from 'react';
import { useSelector } from 'react-redux';

/**
 * ProgressBar component displays the current parsing stage and progress percentage.
 */
const ProgressBar = () => {
  const parsingProgress = useSelector((state) => state.parsing.parsingProgress);

  if (!parsingProgress) return null;

  const { stage, percentage } = parsingProgress;

  return (
    <div className="mt-4">
      <h2 className="text-gray-700 mb-2">{stage}</h2>
      <div className="w-full bg-gray-200 rounded-full h-4">
        <div
          className="bg-blue-500 h-4 rounded-full"
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
      <p className="text-gray-600 mt-1">{percentage}% completed</p>
    </div>
  );
};

export default ProgressBar;
