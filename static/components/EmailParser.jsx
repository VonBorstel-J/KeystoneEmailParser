// static/components/EmailParser.jsx

import React, { useState, useEffect, useCallback, useRef, useMemo, useReducer } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Loader,
  AlertCircle,
  FileText,
  X,
  Settings,
  Sun,
  Moon,
} from 'lucide-react';
import { parseEmail } from '@actions/parsingActions';
import socketManager from '@core/socket';
import { debounce } from 'lodash';
import PropTypes from 'prop-types';

// Helper Functions
function getConfidenceColor(level) {
  switch (level.toLowerCase()) {
    case 'high':
      return 'bg-green-500 text-white';
    case 'medium':
      return 'bg-yellow-500 text-white';
    case 'low':
      return 'bg-red-500 text-white';
    default:
      return 'bg-gray-500 text-white';
  }
}

function getFieldColor(field) {
  if (field.toLowerCase().includes('name')) return 'text-blue-600 dark:text-blue-400';
  if (field.toLowerCase().includes('contact')) return 'text-green-600 dark:text-green-400';
  if (field.toLowerCase().includes('address')) return 'text-purple-600 dark:text-purple-400';
  if (['insurancecompany', 'claimnumber', 'dateofloss'].includes(field.toLowerCase())) return 'text-yellow-600 dark:text-yellow-400';
  if (['type', 'details'].includes(field.toLowerCase())) return 'text-red-600 dark:text-red-400';
  return 'text-gray-900 dark:text-gray-100';
}

// Memoized SchemaViewer Component
const SchemaViewer = React.memo(({ schema, schemaData = {}, completionPercentage = 0, missingFields = [], onManualOverride, confidenceLevels = {} }) => {
  const renderSection = useCallback(([section, fields]) => {
    const bgColorClass = schemaData?.[section]?.[field]
      ? 'bg-green-50 dark:bg-green-700'
      : 'bg-red-50 dark:bg-red-700';

    return (
      <div key={section} className="border-t pt-4 mt-4">
        <h3 className="font-medium mb-2 text-gray-800 dark:text-gray-200">{section}</h3>
        <div className="space-y-2">
          {Object.entries(fields).map(([field, required]) => {
            const fieldBgColor = schemaData?.[section]?.[field]
              ? 'bg-green-50 dark:bg-green-700'
              : 'bg-red-50 dark:bg-red-700';

            return (
              <div
                key={`${section}-${field}`}
                className={`p-2 rounded ${fieldBgColor} flex justify-between items-center`}
              >
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{field}</div>
                  <div className="text-sm text-gray-700 dark:text-gray-300">
                    {schemaData?.[section]?.[field] ? schemaData[section][field] : 'Not Found'}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {confidenceLevels?.[`${section}.${field}`] && (
                    <span className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(confidenceLevels[`${section}.${field}`])}`}>
                      {confidenceLevels[`${section}.${field}`]}
                    </span>
                  )}
                  {!schemaData?.[section]?.[field] && (
                    <button
                      onClick={() => onManualOverride(section, field, prompt(`Enter value for ${field}:`, ''))}
                      className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-600"
                    >
                      Override
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }, [schemaData, confidenceLevels, onManualOverride]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="mb-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">Parsing Results</h2>
          <div className="text-sm text-gray-500 dark:text-gray-300">
            {completionPercentage}% {completionPercentage === 100 ? 'Complete' : 'In Progress'}
          </div>
        </div>
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full mt-2">
          <div
            className="bg-blue-600 dark:bg-blue-500 h-2 rounded-full"
            style={{ width: `${completionPercentage}%` }}
          />
        </div>
      </div>

      {/* Schema Sections */}
      {Object.entries(schema).map(renderSection)}

      {/* Missing Fields Summary */}
      {missingFields?.length > 0 && (
        <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-700 rounded">
          <h4 className="font-medium text-gray-900 dark:text-gray-100">Missing Fields</h4>
          <ul className="mt-2 space-y-1">
            {missingFields.map(field => (
              <li key={field} className="text-sm text-gray-700 dark:text-gray-300">
                • {field}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
});

SchemaViewer.propTypes = {
  schema: PropTypes.object.isRequired,
  schemaData: PropTypes.object,
  completionPercentage: PropTypes.number,
  missingFields: PropTypes.array,
  onManualOverride: PropTypes.func.isRequired,
  confidenceLevels: PropTypes.object,
};

// Memoized ResultsDisplay Component
const ResultsDisplay = React.memo(({ schema, schemaData = {}, connecting, onManualOverride }) => (
  !connecting && schemaData && (
    <SchemaViewer 
      schema={schema}
      schemaData={schemaData} 
      completionPercentage={schemaData.completionPercentage || 0} 
      missingFields={schemaData.missingFields || []} 
      onManualOverride={onManualOverride} 
      confidenceLevels={schemaData.confidenceLevels || {}} 
    />
  )
));

ResultsDisplay.propTypes = {
  schema: PropTypes.object.isRequired,
  schemaData: PropTypes.object,
  connecting: PropTypes.bool.isRequired,
  onManualOverride: PropTypes.func.isRequired,
};

// Memoized ConnectionStatus Component
const ConnectionStatus = React.memo(({ status = false, connecting = false }) => (
  <div className="flex items-center gap-2 mb-4">
    <div
      className={`w-2 h-2 rounded-full ${
        status ? 'bg-green-500' :
        connecting ? 'bg-yellow-500' : 'bg-red-500'
      }`}
    />
    <span className="text-sm text-gray-600 dark:text-gray-300">
      {status ? 'Connected' : connecting ? 'Connecting...' : 'Disconnected'}
    </span>
  </div>
));

ConnectionStatus.propTypes = {
  status: PropTypes.bool,
  connecting: PropTypes.bool,
};

// HighlightedEmail Component (Moved Outside Parent Component)
const HighlightedEmail = React.memo(({ content = '', recognizedFields = {} }) => {
  const highlightedContent = content.split('\n').map((line, index) => {
    let highlightedLine = line;
    Object.keys(recognizedFields).forEach(field => {
      const value = recognizedFields[field];
      if (value && line.includes(value)) {
        const regex = new RegExp(`(${value})`, 'g');
        highlightedLine = highlightedLine.replace(regex, `<span class="${getFieldColor(field)}">${'$1'}</span>`);
      }
    });
    return <div key={`line-${index}-${line.substring(0, 10)}`} dangerouslySetInnerHTML={{ __html: highlightedLine }} />;
  });

  return <div className="font-mono whitespace-pre-wrap">{highlightedContent}</div>;
});

HighlightedEmail.propTypes = {
  content: PropTypes.string,
  recognizedFields: PropTypes.object,
};

// Error Boundary Component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // You can log the error to an error reporting service here
    console.error("ErrorBoundary caught an error", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="mt-6 bg-red-50 dark:bg-red-100 border border-red-200 dark:border-red-400 rounded-lg p-4 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 dark:text-red-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <p className="text-sm text-red-700 dark:text-red-800">Something went wrong:</p>
            <pre className="text-sm text-red-700 dark:text-red-800 mt-1">{this.state.error.toString()}</pre>
          </div>
        </div>
      );
    }

    return this.props.children; 
  }
}

function EmailParser() {
  const dispatch = useDispatch();
  const parsingResult = useSelector(state => state.parsing?.parsedData);

  // Consolidated State Management
  const initialState = {
    parsing: false,
    socket: { status: false, connecting: true },
    ui: { darkMode: false, language: 'en' },
    themeColors: { primary: '#3b82f6', secondary: '#ef4444' },
    isSettingsOpen: false,
    parsingProgress: 0,
    schemaData: {},
    missingFields: [],
    completionPercentage: 0,
    recognizedFields: {},
    confidenceLevels: {},
    manualOverrides: {},
    error: null,
    retryCount: 0,
  };

  function reducer(state, action) {
    switch (action.type) {
      case 'UPDATE_STATE':
        return { ...state, ...action.payload };
      case 'INCREMENT_RETRY':
        return { ...state, retryCount: state.retryCount + 1 };
      case 'RESET_RETRY':
        return { ...state, retryCount: 0 };
      default:
        return state;
    }
  }

  const [appState, dispatchState] = useReducer(reducer, initialState);

  const {
    parsing,
    socket: { status: socketStatus, connecting },
    ui: { darkMode, language },
    themeColors,
    isSettingsOpen,
    parsingProgress,
    schemaData,
    missingFields,
    completionPercentage,
    recognizedFields,
    confidenceLevels,
    manualOverrides,
    error,
    retryCount,
  } = appState;

  const [email, setEmail] = useState('');
  const [toasts, setToasts] = useState([]);
  const abortControllerRef = useRef(null);

  // Toast Manager - Moved to top before other hooks
  const ToastManager = useMemo(() => ({
    add: (message, type) => {
      const id = Date.now();  // Original code
      setToasts(prev => [...prev, { id: `${id}-${Math.random()}`, message, type }]); // Make `key` unique
      setTimeout(() => ToastManager.remove(id), 3000);
    },
    remove: (id) => setToasts(prev => prev.filter(t => t.id !== id)),
  }), []);

  // Update App State Function
  const updateAppState = useCallback((updates) => {
    dispatchState({ type: 'UPDATE_STATE', payload: updates });
  }, []);

  // Translations
  const translations = useMemo(() => ({
    en: { /* ...translations as provided... */ },
    es: { /* ...translations as provided... */ },
    // Add more languages as needed
  }), []);

  const t = useCallback((key) => translations[language]?.[key] || key, [translations, language]);

  // Sample Email Templates
  const sampleEmails = useMemo(() => ({
    complete: `Subject: Claim Assignment - Water Damage Inspection
From: claims@insurance.com
To: inspector@company.com

Insurance Company: State Farm
Claim Number: ABC123456
Date of Loss: 2024-03-15

Insured Information:
Name: John Smith
Contact: +1-555-123-4567
Address: 123 Main St, Anytown, USA

Please inspect water damage from burst pipe. Property currently vacant.
Tenant reported issue on March 14th.

Additional Details:
- Emergency mitigation completed
- Access code: 1234
- Contact property manager for entry

Regards,
Claims Department`,
    partial: `Subject: Claim Assignment - Fire Damage Inspection
From: claims@insurance.com
To: inspector@company.com

Insurance Company: Allstate
Claim Number: XYZ789012
Date of Loss: 2024-04-20

Insured Information:
Name: Jane Doe
Contact: +1-555-987-6543

Please inspect fire damage. Property currently occupied.

Regards,
Claims Department`,
    differentType: `Subject: Claim Assignment - Theft Investigation
From: claims@insurance.com
To: investigator@company.com

Insurance Company: Geico
Claim Number: LMN456789
Date of Loss: 2024-05-10

Insured Information:
Name: Mike Johnson
Contact: +1-555-654-3210
Address: 456 Elm St, Othertown, USA

Please investigate the theft reported on May 9th.

Regards,
Claims Department`,
  }), []);

  // Schema Definition
  const schema = useMemo(() => ({
    'Requesting Party': { Name: true, Contact: true, Address: false },
    'Insured Information': { Name: true, Contact: true, Address: true },
    'Adjuster Information': { Name: false, Contact: false, Email: false },
    'Assignment Information': { InsuranceCompany: true, ClaimNumber: true, DateOfLoss: true },
    'Assignment Type': { Type: true, Details: false },
  }), []);

  // Highlight Patterns
  const highlightPatterns = useMemo(() => ({
    name: /Name:\s*(.*)/i,
    contact: /Contact:\s*(.*)/i,
    address: /Address:\s*(.*)/i,
    insuranceCompany: /Insurance Company:\s*(.*)/i,
    claimNumber: /Claim Number:\s*(.*)/i,
    dateOfLoss: /Date of Loss:\s*(.*)/i,
    type: /Subject:\s*(.*)/i,
    details: /Please inspect (.*)\./i,
  }), []);

  // Field Detector
  const fieldDetector = useMemo(() => ({
    patterns: {
      name: /Name:\s*(.*)/i,
      contact: /Contact:\s*(.*)/i,
      address: /Address:\s*(.*)/i,
      insuranceCompany: /Insurance Company:\s*(.*)/i,
      claimNumber: /Claim Number:\s*(.*)/i,
      dateOfLoss: /Date of Loss:\s*(.*)/i,
      type: /Subject:\s*(.*)/i,
      details: /Please inspect (.*)\./i,
    },
    detect: (text, type) => 
      text.match(fieldDetector.patterns[type])?.[1]
  }), []);

  // Define toggleTheme with useCallback
  const toggleTheme = useCallback(() => {
    updateAppState(prevState => ({
      ui: { ...prevState.ui, darkMode: !prevState.ui.darkMode },
    }));
    document.documentElement.classList.toggle('dark');
    ToastManager.add('Theme updated', 'success');
  }, [updateAppState, ToastManager]);

  // Theme Manager
  const ThemeManager = useMemo(() => ({
    toggle: toggleTheme,
    init: () => {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (prefersDark !== darkMode) {
        toggleTheme();
      }
    }
  }), [toggleTheme, darkMode]);

  // Handle Error
  const handleError = useCallback((error, context) => {
    updateAppState({ error: error.message });
    ToastManager.add(
      context ? `${context}: ${error.message}` : error.message, 
      'error'
    );
  }, [ToastManager, updateAppState]);

  // Socket Manager
  const SocketManager = useMemo(() => ({
    connect: () => updateAppState({
      socket: { status: true, connecting: false },
    }),
    disconnect: () => updateAppState({
      socket: { status: false, connecting: false },
    }),
    handleError: (error) => {
      console.error('Socket error:', error);
      handleError(error, 'Socket');
    }
  }), [updateAppState, handleError]);

  // Initialize Theme on Mount
  useEffect(() => {
    ThemeManager.init();
  }, [ThemeManager]);

  // Load draft and settings from localStorage on mount
  useEffect(() => {
    const savedEmail = localStorage.getItem('draftEmail');
    const savedLanguage = localStorage.getItem('language');
    const savedTheme = localStorage.getItem('themeColors');
    if (savedEmail) setEmail(savedEmail);
    if (savedLanguage) updateAppState({ ui: { ...appState.ui, language: savedLanguage } });
    if (savedTheme) updateAppState({ themeColors: JSON.parse(savedTheme) });
  }, [updateAppState, appState.ui]);

  // Auto-save to localStorage
  useEffect(() => { localStorage.setItem('draftEmail', email); }, [email]);
  useEffect(() => { localStorage.setItem('language', language); }, [language]);
  useEffect(() => {
    localStorage.setItem('themeColors', JSON.stringify(themeColors));
    document.documentElement.style.setProperty('--color-primary', themeColors.primary);
    document.documentElement.style.setProperty('--color-secondary', themeColors.secondary);
  }, [themeColors]);

  // Dark mode based on system preference with cleanup
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e) => {
      if (e.matches !== darkMode) {
        ThemeManager.toggle();
      }
    };
    
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [darkMode, ThemeManager]);

  // Toast Notifications
  const renderToasts = useMemo(() => (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`flex items-center p-4 rounded-lg shadow-lg ${
            toast.type === 'success' ? 'bg-green-100 dark:bg-green-700' :
            toast.type === 'error' ? 'bg-red-100 dark:bg-red-700' :
            'bg-blue-100 dark:bg-blue-700'
          }`}
        >
          <div className="flex-1 text-sm text-gray-800 dark:text-gray-100">{toast.message}</div>
          <button onClick={() => ToastManager.remove(toast.id)}>
            <X className="w-4 h-4 text-gray-600 dark:text-gray-200" />
          </button>
        </div>
      ))}
    </div>
  ), [toasts, ToastManager]);

  // Socket Connection Cleanup and Management
  useEffect(() => {
    const socket = socketManager.getSocket();
    let mounted = true;  // Add mount tracking

    if (socket) {
      const handleConnect = () => {
        if (mounted) updateAppState({
          socket: { status: true, connecting: false },
        });
      };

      const handleDisconnect = () => {
        if (mounted) updateAppState({
          socket: { status: false, connecting: false },
        });
      };

      const handleSocketError = (error) => {
        if (mounted) {
          console.error('Socket error:', error);
          handleError(error, 'Socket');
        }
      };

      socket.on('connect', handleConnect);
      socket.on('disconnect', handleDisconnect);
      socket.on('error', handleSocketError);

      // Initial status
      if (mounted) {
        updateAppState({
          socket: { status: socket.connected, connecting: !socket.connected },
        });
      }

      return () => {
        mounted = false;
        socket.off('connect', handleConnect);
        socket.off('disconnect', handleDisconnect);
        socket.off('error', handleSocketError);
      };
    }
  }, [SocketManager, updateAppState, handleError]);

  // Map parsed data to schema
  const mapToSchema = useCallback((data) => {
    const mapped = {};
    Object.keys(schema).forEach(section => {
      mapped[section] = {};
      Object.keys(schema[section]).forEach(field => {
        mapped[section][field] = data?.[section]?.[field] ?? null;
        if (manualOverrides?.[`${section}.${field}`]) {
          mapped[section][field] = manualOverrides[`${section}.${field}`];
        }
      });
    });
    return mapped;
  }, [schema, manualOverrides]);

  // Calculate completion percentage
  const calculateCompletion = useCallback((mappedData) => {
    let total = 0;
    let found = 0;
    Object.keys(schema).forEach(section => {
      Object.keys(schema[section]).forEach(field => {
        total += 1;
        if (mappedData[section] && mappedData[section][field]) found += 1;
      });
    });
    const percentage = total === 0 ? 0 : Math.round((found / total) * 100);
    updateAppState({ completionPercentage: percentage });
  }, [schema, updateAppState]);

  // Identify missing required fields
  const identifyMissingFields = useCallback((mappedData) => {
    const missing = [];
    Object.keys(schema).forEach(section => {
      Object.keys(schema[section]).forEach(field => {
        if (schema[section][field] && (!mappedData[section] || !mappedData[section][field])) {
          missing.push(`${section} - ${field}`);
        }
      });
    });
    updateAppState({ missingFields: missing });
  }, [schema, updateAppState]);

  // Handle Submit without Recursive Calls
  const handleSubmit = useCallback(async (e) => {
    if (e) e.preventDefault();

    // Cancel any in-flight requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    updateAppState({ parsing: true, parsingProgress: 0, error: null });

    try {
      const socket = socketManager.getSocket();
      if (!socket || !socketStatus) throw new Error('Socket error occurred');

      const parsedData = await dispatch(parseEmail(
        { emailContent: email, parserOption: 'enhanced' },
        socket,
        (progress) => updateAppState({ parsingProgress: progress }),
        abortController.signal
      ));

      // Map parsed data to schema
      const mappedData = mapToSchema(parsedData);
      console.log('Mapped Data:', mappedData); // Debugging

      calculateCompletion(mappedData);
      identifyMissingFields(mappedData);
      updateAppState({
        schemaData: mappedData,
        recognizedFields: parsedData.recognizedFields || {},
        confidenceLevels: parsedData.confidenceLevels || {},
      });
      ToastManager.add('Email parsed successfully', 'success');
      dispatchState({ type: 'RESET_RETRY' });
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Parsing request was aborted');
      } else {
        handleError(err, 'Parsing');
        if (retryCount < 3) {
          dispatchState({ type: 'INCREMENT_RETRY' });
          ToastManager.add(`Retrying... (${retryCount + 1})`, 'error');
          // Implement retry logic without calling handleSubmit again
          // Optionally, you can use a timeout to retry after a delay
          setTimeout(() => {
            handleSubmit(e);
          }, 1000);
        } else {
          ToastManager.add('Failed to parse email after multiple attempts.', 'error');
        }
      }
    } finally {
      updateAppState({ parsing: false, parsingProgress: 0 });
    }
  }, [dispatch, email, socketStatus, ToastManager, handleError, updateAppState, retryCount, mapToSchema, calculateCompletion, identifyMissingFields]);

  // Handle Sample Email Loading
  const handleSampleEmail = useCallback((type = 'complete') => {
    const sample = sampleEmails[type];
    setEmail(sample);
    ToastManager.add('Sample email loaded', 'success');
  }, [sampleEmails, ToastManager]);

  // Copy to Clipboard
  const copyToClipboard = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(schemaData, null, 2));
      ToastManager.add('Copied to clipboard', 'success');
    } catch (err) {
      ToastManager.add('Failed to copy', 'error');
    }
  }, [schemaData, ToastManager]);

  // Save as JSON
  const saveAsJSON = useCallback(() => {
    const blob = new Blob([JSON.stringify(schemaData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'parsed_email.json';
    a.click();
    URL.revokeObjectURL(url);
    ToastManager.add('JSON file downloaded', 'success');
  }, [schemaData, ToastManager]);

  // Export to PDF
  const exportToPDF = useCallback(() => {
    window.print();
    ToastManager.add('Exported to PDF', 'success');
  }, [ToastManager]);

  // Print Results
  const printResults = useCallback(() => {
    window.print();
  }, []);

  // Handle Manual Override
  const handleManualOverride = useCallback((section, field, value) => {
    if (value) {
      updateAppState(prevState => ({
        manualOverrides: { ...prevState.manualOverrides, [`${section}.${field}`]: value },
      }));
      ToastManager.add(`Overridden ${field}`, 'success');
    }
  }, [ToastManager, updateAppState]);

  // Key Down Handler
  const handleKeyDown = useCallback((e) => {
    if (e.ctrlKey && e.key === 'Enter') {
      handleSubmit(e);
    }
    if (e.key === 'Escape') {
      setEmail('');
      ToastManager.add('Input cleared', 'success');
    }
  }, [handleSubmit, ToastManager]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Debounced Live Preview
  const debouncedHandleSubmit = useMemo(() => debounce(handleSubmit, 500), [handleSubmit]);

  useEffect(() => {
    if (email.trim()) {
      debouncedHandleSubmit(new Event('submit'));
    }
    return () => {
      debouncedHandleSubmit.cancel();
    };
  }, [email, debouncedHandleSubmit]);

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Toast Notifications */}
        {renderToasts}

        {/* Settings Modal */}
        {isSettingsOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg w-11/12 max-w-md p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Theme Settings</h2>
                <button onClick={() => updateAppState({ isSettingsOpen: false })}>
                  <X className="w-5 h-5 text-gray-600 dark:text-gray-200" />
                </button>
              </div>
              <form className="space-y-4">
                <div>
                  <label htmlFor="language" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Language
                  </label>
                  <select
                    id="language"
                    value={language}
                    onChange={(e) => updateAppState({ ui: { ...appState.ui, language: e.target.value } })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="en">English</option>
                    <option value="es">Español</option>
                    {/* Add more languages here */}
                  </select>
                </div>
                <div>
                  <label htmlFor="primaryColor" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Primary Color
                  </label>
                  <input
                    type="color"
                    id="primaryColor"
                    value={themeColors.primary}
                    onChange={(e) => updateAppState(prevState => ({ themeColors: { ...prevState.themeColors, primary: e.target.value } }))}
                    className="w-full h-10 p-0 border-none"
                  />
                </div>
                <div>
                  <label htmlFor="secondaryColor" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Secondary Color
                  </label>
                  <input
                    type="color"
                    id="secondaryColor"
                    value={themeColors.secondary}
                    onChange={(e) => updateAppState(prevState => ({ themeColors: { ...prevState.themeColors, secondary: e.target.value } }))}
                    className="w-full h-10 p-0 border-none"
                  />
                </div>
              </form>
              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => updateAppState({ isSettingsOpen: false })}
                  className="px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="max-w-6xl mx-auto py-8 px-4">
          {/* Top Controls */}
          <div className="flex justify-between items-center mb-4">
            <div className="flex space-x-2">
              {/* Sample Email Buttons */}
              {useMemo(() => [
                { type: 'complete', label: '1' },
                { type: 'partial', label: '2' },
                { type: 'differentType', label: '3' }
              ], []).map(({ type, label }) => (
                <button
                  key={type}
                  onClick={() => handleSampleEmail(type)}
                  className="inline-flex items-center text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-600"
                  title={`Load Sample Email ${label}`}
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Load Sample Email {label}
                </button>
              ))}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => updateAppState({ isSettingsOpen: true })}
                className="flex items-center text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white focus:outline-none"
                title="Theme Settings"
              >
                <Settings className="w-5 h-5 mr-1" />
                Settings
              </button>
              <button
                onClick={ThemeManager.toggle}
                className="flex items-center text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white focus:outline-none"
                title="Toggle Dark Mode"
              >
                {darkMode ? <Sun className="w-5 h-5 mr-1" /> : <Moon className="w-5 h-5 mr-1" />}
                {darkMode ? 'Light Mode' : 'Dark Mode'}
              </button>
            </div>
          </div>

          {/* Connection Status */}
          <ConnectionStatus status={socketStatus} connecting={connecting} />

          {/* Header */}
          <div className="flex items-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Email Parser</h1>
          </div>

          {/* Main Form */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="emailContent" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Email Content
                </label>
                <HighlightedEmail content={email} recognizedFields={recognizedFields} />
                <textarea
                  id="emailContent"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-64 px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 overflow-auto font-mono"
                  placeholder="Email Content"
                  spellCheck="false"
                />
                <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Characters: {email.length}
                </div>
              </div>

              {/* Progress Bar */}
              {parsingProgress > 0 && (
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-4">
                  <div
                    className="bg-blue-600 dark:bg-blue-500 h-2.5 rounded-full"
                    style={{ width: `${parsingProgress}%` }}
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={parsing || !email.trim() || !socketStatus}
                className={`w-full bg-blue-600 dark:bg-blue-500 text-white h-12 px-6 rounded-lg font-medium
                         hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 
                         focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed
                         flex items-center justify-center`}
              >
                {parsing ? (
                  <>
                    <Loader className="w-5 h-5 mr-2 animate-spin" />
                    Parsing...
                  </>
                ) : (
                  'Parse Email'
                )}
              </button>
            </form>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mt-6 bg-red-50 dark:bg-red-100 border border-red-200 dark:border-red-400 rounded-lg p-4 flex items-start">
              <AlertCircle className="w-5 h-5 text-red-500 dark:text-red-600 mt-0.5 mr-3 flex-shrink-0" />
              <div>
                <p className="text-sm text-red-700 dark:text-red-800">Error:</p>
                <pre className="text-sm text-red-700 dark:text-red-800 mt-1">{error}</pre>
              </div>
            </div>
          )}

          {/* Results Display */}
          <ResultsDisplay 
            schema={schema} 
            schemaData={schemaData} 
            connecting={connecting} 
            onManualOverride={handleManualOverride} 
          />

          {/* Highlighted Email */}
          {schemaData && (
            <div className="mt-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">Smart Highlighting</h2>
                <HighlightedEmail content={email} recognizedFields={recognizedFields} />
              </div>
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
}

EmailParser.propTypes = {};

export default EmailParser;
