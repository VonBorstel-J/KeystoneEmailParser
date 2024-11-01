// frontend/components/ResultViewer/OriginalView.jsx
import React from 'react';

/**
 * OriginalView component displays the raw parsed data.
 * @param {Object} props - Component properties.
 * @param {Object} props.data - The parsed data to display.
 */
const OriginalView = ({ data }) => (
  <pre className="bg-gray-100 p-4 rounded overflow-auto">
    {JSON.stringify(data, null, 2)}
  </pre>
);

export default OriginalView;
