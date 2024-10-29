// static/components/ResultViewer/JsonView.jsx

import React from 'react';
import PropTypes from 'prop-types';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { dark } from 'react-syntax-highlighter/dist/esm/styles/prism';

/**
 * JsonView Component
 * Displays the parsed data in JSON format with syntax highlighting.
 *
 * @param {Object} props
 * @param {Object} props.data - The parsed JSON data.
 */
const JsonView = ({ data }) => (
  <div className="json-view overflow-auto bg-gray-50 dark:bg-gray-700 rounded-md p-4">
    <SyntaxHighlighter language="json" style={dark} showLineNumbers>
      {JSON.stringify(data, null, 2)}
    </SyntaxHighlighter>
  </div>
);

JsonView.propTypes = {
  data: PropTypes.object.isRequired,
};

export default React.memo(JsonView);
