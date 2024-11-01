import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import ParserForm from './components/ParsingOverlay/ParserForm';
import ProgressBar from './components/ParsingOverlay/ProgressBar';
import ResultViewer from './components/ResultViewer';
import ToastContainer from './components/common/ToastContainer';
import Header from './components/common/Header';
import socketManager from './utils/socket';

const App = () => {
  const [connectionStatus, setConnectionStatus] = useState({
    isConnected: false,
    isConnecting: false,
    error: null
  });
  const dispatch = useDispatch();
  
  const parsingProgress = useSelector((state) => state.parsing.parsingProgress);
  const parsingResult = useSelector((state) => state.parsing.parsingResult);
  const error = useSelector((state) => state.parsing.error);

  // Initialize socket connection
  useEffect(() => {
    let mounted = true;

    const initializeSocket = async () => {
      if (!mounted || connectionStatus.isConnecting) return;

      try {
        setConnectionStatus(prev => ({ ...prev, isConnecting: true, error: null }));
        
        // Set up event handlers before connecting
        socketManager.on('connect', () => {
          if (mounted) {
            setConnectionStatus({
              isConnected: true,
              isConnecting: false,
              error: null
            });
            dispatch({
              type: 'ADD_TOAST',
              payload: {
                id: Date.now(),
                type: 'success',
                message: 'Connected to server'
              }
            });
          }
        });

        socketManager.on('disconnect', () => {
          if (mounted) {
            setConnectionStatus(prev => ({
              ...prev,
              isConnected: false,
              error: 'Disconnected from server'
            }));
            dispatch({
              type: 'ADD_TOAST',
              payload: {
                id: Date.now(),
                type: 'warning',
                message: 'Disconnected from server'
              }
            });
          }
        });

        socketManager.on('connect_error', (error) => {
          if (mounted) {
            console.error('Socket connection error:', error);
            setConnectionStatus({
              isConnected: false,
              isConnecting: false,
              error: 'Failed to connect to server'
            });
            dispatch({
              type: 'ADD_TOAST',
              payload: {
                id: Date.now(),
                type: 'error',
                message: 'Connection error: ' + error.message
              }
            });
          }
        });

        // Attempt connection
        await socketManager.connect();

      } catch (error) {
        console.error('Socket initialization error:', error);
        if (mounted) {
          setConnectionStatus({
            isConnected: false,
            isConnecting: false,
            error: error.message
          });
        }
      }
    };

    initializeSocket().catch(console.error);

    // Cleanup function
    return () => {
      mounted = false;
      try {
        socketManager.disconnect();
      } catch (error) {
        console.error('Error during socket cleanup:', error);
      }
    };
  }, [dispatch]);

  // Connection retry handler
  const handleRetryConnection = async () => {
    try {
      setConnectionStatus(prev => ({ ...prev, isConnecting: true, error: null }));
      await socketManager.connect();
    } catch (error) {
      console.error('Retry connection failed:', error);
      setConnectionStatus({
        isConnected: false,
        isConnecting: false,
        error: 'Retry failed: ' + error.message
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <Header />
      <main className="container mx-auto p-4 flex-grow">
        {/* Connection Status */}
        {!connectionStatus.isConnected && (
          <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded relative mb-4">
            <span className="block sm:inline">
              {connectionStatus.isConnecting ? (
                <div className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-yellow-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Connecting to server...
                </div>
              ) : (
                'Not connected to server'
              )}
            </span>
          </div>
        )}

        {/* Error Display */}
        {(error || connectionStatus.error) && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">
              {error || connectionStatus.error}
            </span>
            {!connectionStatus.isConnected && (
              <button
                onClick={handleRetryConnection}
                disabled={connectionStatus.isConnecting}
                className="mt-2 text-sm font-medium text-red-600 hover:text-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {connectionStatus.isConnecting ? 'Retrying...' : 'Try reconnecting'}
              </button>
            )}
          </div>
        )}
        
        {/* Main Content */}
        {connectionStatus.isConnected && (
          <>
            {!parsingProgress && !parsingResult && <ParserForm />}

            {parsingProgress && (
              <div className="mb-4">
                <ProgressBar />
                <p className="text-gray-700 mt-2">
                  Current Stage: {parsingProgress.stage} - {parsingProgress.percentage}% complete
                </p>
              </div>
            )}

            {parsingResult && (
              <div className="mb-4">
                <ResultViewer />
                <button
                  className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded mt-4 transition-colors duration-200"
                  onClick={() => window.location.reload()}
                >
                  Start New Parsing
                </button>
              </div>
            )}
          </>
        )}
      </main>
      <ToastContainer />
    </div>
  );
};

export default App;