// frontend/App.jsx
import React from 'react';
import { useSelector } from 'react-redux';
import ParserForm from './components/ParsingOverlay/ParserForm';
import ProgressBar from './components/ParsingOverlay/ProgressBar';
import ResultViewer from './components/ResultViewer';
import ToastContainer from './components/common/ToastContainer';
import Header from './components/common/Header';

/**
 * App component serves as the root of the application.
 * It includes the Header, ParserForm, ProgressBar, ResultViewer, and ToastContainer.
 */
const App = () => {
  const parsingProgress = useSelector((state) => state.parsing.parsingProgress);
  const parsingResult = useSelector((state) => state.parsing.parsingResult);
  const error = useSelector((state) => state.parsing.error);

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <Header />
      <main className="container mx-auto p-4 flex-grow">
        {/* Display error if it exists */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
        )}
        
        {/* Hide the form if parsing is in progress */}
        {!parsingProgress && !parsingResult && <ParserForm />}

        {/* Display progress if parsing is in progress */}
        {parsingProgress && (
          <div className="mb-4">
            <ProgressBar />
            <p className="text-gray-700 mt-2">
              Current Stage: {parsingProgress.stage} - {parsingProgress.percentage}% complete
            </p>
          </div>
        )}

        {/* Show results after parsing is complete */}
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
      <ToastContainer />
    </div>
  );
};

export default App;
