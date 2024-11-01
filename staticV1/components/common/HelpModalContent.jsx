// static/components/common/HelpModalContent.jsx
import React from 'react';

const HelpModalContent = () => {
  return (
    <div className="prose">
      <p>Welcome to Email Parser Pro! Follow these steps to parse your emails:</p>
      <ol>
        <li>Choose a sample email or paste your own content in the text area</li>
        <li>Optionally upload a related document image</li>
        <li>Select a parser option from the dropdown</li>
        <li>Click "Parse Email" to start the process</li>
        <li>View the results in JSON, human-readable, or original format</li>
        <li>Download the results in CSV or PDF format if needed</li>
      </ol>
      <h4>Features:</h4>
      <ul>
        <li>Real-time parsing progress visualization</li>
        <li>Support for document images</li>
        <li>Multiple output formats</li>
        <li>Export capabilities</li>
        <li>Dark mode support</li>
      </ul>
      <p>For additional support or questions, please contact our support team.</p>
    </div>
  );
};

export default HelpModalContent;
