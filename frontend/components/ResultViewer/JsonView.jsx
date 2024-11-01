// frontend/components/ResultViewer/JsonView.jsx
import React from 'react';

/**
 * JsonView component displays the parsed data as formatted JSON.
 * @param {Object} props - Component properties.
 * @param {Object} props.data - The parsed data to display.
 */
const JsonView = ({ data }) => (
  <pre className="bg-gray-100 p-4 rounded overflow-auto">
    {JSON.stringify(data, null, 2)}
  </pre>
);

export default JsonView;
