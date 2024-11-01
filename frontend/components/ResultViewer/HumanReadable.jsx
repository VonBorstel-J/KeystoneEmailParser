// frontend/components/ResultViewer/HumanReadable.jsx
import React from 'react';

/**
 * HumanReadable component displays the parsed data in a readable format.
 * @param {Object} props - Component properties.
 * @param {Object} props.data - The parsed data to display.
 */
const HumanReadable = ({ data }) => {
  // Example implementation; adjust based on actual data structure
  return (
    <div>
      {Object.entries(data).map(([section, fields]) => (
        <div key={section} className="mb-4">
          <h3 className="text-lg font-semibold">{section}</h3>
          <ul className="list-disc list-inside">
            {Object.entries(fields).map(([key, value]) => (
              <li key={key}>
                <strong>{key}:</strong> {Array.isArray(value) ? value.join(', ') : value}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

export default HumanReadable;
