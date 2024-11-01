// static/components/ResultViewer/index.jsx
import React from 'react';
import { useSelector } from 'react-redux';

const ResultViewer = () => {
  const parsedData = useSelector((state) => state.parsing.parsedData);

  if (!parsedData) return null;

  return (
    <div>
      <h2>Parsed Results</h2>
      <pre>{JSON.stringify(parsedData, null, 2)}</pre>
    </div>
  );
};

export default ResultViewer;
