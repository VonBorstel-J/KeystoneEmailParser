// frontend/components/App.jsx
import React from 'react';
import { useSelector } from 'react-redux';
import ParserForm from './ParsingOverlay/ParserForm';
import ProgressBar from './ParsingOverlay/ProgressBar';
import ResultViewer from './ResultViewer';
import ToastContainer from './common/ToastContainer';
import Header from './common/Header';

/**
 * App component serves as the root of the application.
 * It includes the Header, ParserForm, ProgressBar, ResultViewer, and ToastContainer.
 */
const App = () => {
  const { parsingProgress, parsingResult, error, toasts } = useSelector((state) => state.parsing);

  return (
    <div className="min-h-screen flex flex-col bg-gray-100">
      <Header />
      <main className="container mx-auto p-4 flex-grow">
        {/* Display error message */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        {/* Conditional rendering of form, progress, and results */}
        {!parsingProgress && !parsingResult && <ParserForm />}
        {parsingProgress && (
          <div className="mb-4">
            <ProgressBar />
            <p className="text-gray-700 mt-2">
              {`Stage: ${parsingProgress.stage} - ${parsingProgress.percentage}% complete`}
            </p>
          </div>
        )}
        {parsingResult && (
          <div className="mb-4">
            <ResultViewer />
            <button
              className="bg-blue-500 text-white px-4 py-2 rounded mt-4"
              onClick={() => window.location.reload()}
            >
              Start New Parsing
            </button>
          </div>
        )}
      </main>
      {/* Toast notifications */}
      <ToastContainer toasts={toasts} />
    </div>
  );
};

export default App;
