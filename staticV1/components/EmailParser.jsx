// EmailParser.jsx

import React, {
  useEffect,
  useCallback,
  useRef,
  useMemo,
  useReducer,
  useState,
} from 'react';
import {
  Loader,
  AlertCircle,
  FileText,
  X,
  Settings,
  Sun,
  Moon,
} from 'lucide-react';
import PropTypes from 'prop-types';
import { debounce } from 'lodash';

// Define a basic validateEmailContent function
const validateEmailContent = (emailContent) => {
  if (!emailContent || emailContent.trim() === '') {
    return 'Email content is empty';
  }
  // Add more validation rules if needed
  return null;
};

// Define a basic themeManager
const themeManager = {
  currentTheme: 'light',
  initialize() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      this.currentTheme = savedTheme;
      document.documentElement.classList.toggle('dark', this.currentTheme === 'dark');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      this.currentTheme = prefersDark ? 'dark' : 'light';
      document.documentElement.classList.toggle('dark', prefersDark);
    }
  },
  toggleTheme() {
    this.currentTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.classList.toggle('dark', this.currentTheme === 'dark');
    localStorage.setItem('theme', this.currentTheme);
  },
};

// Define a basic socketManager
const socketManager = {
  getSocket() {
    // Return a mock socket object for demonstration purposes
    return {
      connected: false,
      on: () => {},
      off: () => {},
      emit: (event, data, callback) => {
        // Simulate a successful parsing response
        if (event === 'parseEmail') {
          setTimeout(() => {
            callback({
              data: {
                'Requesting Party': { Name: 'John Doe', Contact: 'john@example.com' },
                'Insured Information': { Name: 'Jane Doe', Contact: 'jane@example.com' },
                'Assignment Information': { InsuranceCompany: 'Acme Insurance', ClaimNumber: '12345', DateOfLoss: '2023-01-01' },
                'Assignment Type': { Type: 'Inspection' },
              },
              recognizedFields: {
                'Requesting Party.Name': 'John Doe',
                'Insured Information.Name': 'Jane Doe',
                'Assignment Information.InsuranceCompany': 'Acme Insurance',
              },
              confidenceLevels: {
                'Requesting Party.Name': 'High',
                'Insured Information.Name': 'Medium',
              },
            });
          }, 1000);
        }
      },
    };
  },
};

// Utility Functions
const escapeRegExp = (string) => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
};

const capitalize = (s) =>
  typeof s === 'string' ? s.charAt(0).toUpperCase() + s.slice(1) : '';

// Helper Functions
const getConfidenceColor = (level) => {
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
};

const getFieldColor = (field) => {
  const fieldLower = field.toLowerCase();
  if (fieldLower.includes('name')) return 'text-blue-600 dark:text-blue-400';
  if (fieldLower.includes('contact'))
    return 'text-green-600 dark:text-green-400';
  if (fieldLower.includes('address'))
    return 'text-purple-600 dark:text-purple-400';
  if (
    ['insurancecompany', 'claimnumber', 'dateofloss'].includes(fieldLower)
  )
    return 'text-yellow-600 dark:text-yellow-400';
  if (['type', 'details'].includes(fieldLower))
    return 'text-red-600 dark:text-red-400';
  return 'text-gray-900 dark:text-gray-100';
};

// Mapping and Calculation Functions
const mapToSchema = (data, schema, manualOverrides) => {
  const mapped = {};
  Object.keys(schema).forEach((section) => {
    mapped[section] = {};
    Object.keys(schema[section]).forEach((field) => {
      mapped[section][field] = data?.[section]?.[field] ?? null;
      if (manualOverrides?.[`${section}.${field}`]) {
        mapped[section][field] =
          manualOverrides[`${section}.${field}`];
      }
    });
  });
  return mapped;
};

const calculateCompletion = (mappedData, schema) => {
  let total = 0;
  let found = 0;
  Object.keys(schema).forEach((section) => {
    Object.keys(schema[section]).forEach((field) => {
      total += 1;
      if (
        mappedData[section] &&
        mappedData[section][field]
      )
        found += 1;
    });
  });
  const percentage = total === 0 ? 0 : Math.round((found / total) * 100);
  return percentage;
};

const identifyMissingFields = (mappedData, schema) => {
  const missing = [];
  Object.keys(schema).forEach((section) => {
    Object.keys(schema[section]).forEach((field) => {
      if (
        schema[section][field] &&
        (!mappedData[section] || !mappedData[section][field])
      ) {
        missing.push(`${section} - ${field}`);
      }
    });
  });
  return missing;
};

// Initial State for useReducer
const initialState = {
  socket: { status: false, connecting: true },
  parsing: { active: false, progress: 0, error: null },
  form: { email: '', schemaData: null },
  ui: {
    language: 'en',
    themeColors: { primary: '#3b82f6', secondary: '#ef4444' },
    isSettingsOpen: false,
    toasts: [],
    notifications: [],
  },
  retryCount: 0,
  missingFields: [],
  completionPercentage: 0,
  recognizedFields: {},
  confidenceLevels: {},
  manualOverrides: {},
  error: null,
};

// Reducer Function with Debugging Logs
function reducer(state, action) {
  console.log('Reducer action:', action.type);
  console.log('Payload:', action.payload);

  switch (action.type) {
    case 'SET_EMAIL':
      console.log('Email content set to:', action.payload);
      return { ...state, form: { ...state.form, email: action.payload } };
    case 'CLEAR_EMAIL':
      return { ...state, form: { ...state.form, email: '' } };
    case 'SET_SCHEMA_DATA':
      return {
        ...state,
        form: { ...state.form, schemaData: action.payload.schemaData },
        recognizedFields: action.payload.recognizedFields,
        confidenceLevels: action.payload.confidenceLevels,
      };
    case 'START_PARSING':
      return {
        ...state,
        parsing: { active: true, progress: 0, error: null },
      };
    case 'STOP_PARSING':
      return {
        ...state,
        parsing: {
          active: false,
          progress: action.payload.progress,
          error: action.payload.error,
        },
      };
    case 'INCREMENT_RETRY':
      return { ...state, retryCount: state.retryCount + 1 };
    case 'RESET_RETRY':
      return { ...state, retryCount: 0 };
    case 'UPDATE_SOCKET_STATUS':
      return {
        ...state,
        socket: {
          status: action.payload.status,
          connecting: action.payload.connecting,
        },
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'OPEN_SETTINGS':
      return { ...state, ui: { ...state.ui, isSettingsOpen: true } };
    case 'CLOSE_SETTINGS':
      return { ...state, ui: { ...state.ui, isSettingsOpen: false } };
    case 'SET_LANGUAGE':
      return { ...state, ui: { ...state.ui, language: action.payload } };
    case 'SET_THEME_COLORS':
      return {
        ...state,
        ui: { ...state.ui, themeColors: action.payload },
      };
    case 'ADD_TOAST':
      return {
        ...state,
        ui: {
          ...state.ui,
          toasts: [...state.ui.toasts, action.payload],
        },
      };
    case 'REMOVE_TOAST':
      return {
        ...state,
        ui: {
          ...state.ui,
          toasts: state.ui.toasts.filter(
            (toast) => toast.id !== action.payload
          ),
        },
      };
    case 'SET_MANUAL_OVERRIDE':
      return {
        ...state,
        manualOverrides: {
          ...state.manualOverrides,
          ...action.payload,
        },
      };
    case 'SET_COMPLETION':
      return { ...state, completionPercentage: action.payload };
    case 'SET_MISSING_FIELDS':
      return { ...state, missingFields: action.payload };
    case 'RESET_STATE':
      return initialState;
    default:
      return state;
  }
}

// SchemaViewer Component
const SchemaViewer = React.memo(
  ({
    schema,
    schemaData = {},
    completionPercentage = 0,
    missingFields = [],
    onManualOverride,
    confidenceLevels = {},
  }) => {
    const renderSection = useCallback(
      ([section, fields]) => {
        return (
          <div key={section} className="border-t pt-4 mt-4">
            <h3 className="font-medium mb-2 text-gray-800 dark:text-gray-200">
              {section}
            </h3>
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
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {field}
                      </div>
                      <div className="text-sm text-gray-700 dark:text-gray-300">
                        {schemaData?.[section]?.[field]
                          ? schemaData[section][field]
                          : 'Not Found'}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {confidenceLevels?.[`${section}.${field}`] && (
                        <span
                          className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(
                            confidenceLevels[`${section}.${field}`]
                          )}`}
                        >
                          {confidenceLevels[`${section}.${field}`]}
                        </span>
                      )}
                      {!schemaData?.[section]?.[field] && (
                        <button
                          onClick={() =>
                            onManualOverride(
                              section,
                              field,
                              prompt(`Enter value for ${field}:`, '')
                            )
                          }
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
      },
      [schemaData, confidenceLevels, onManualOverride]
    );

    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="mb-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
              Parsing Results
            </h2>
            <div className="text-sm text-gray-500 dark:text-gray-300">
              {completionPercentage}%{' '}
              {completionPercentage === 100 ? 'Complete' : 'In Progress'}
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
            <h4 className="font-medium text-gray-900 dark:text-gray-100">
              Missing Fields
            </h4>
            <ul className="mt-2 space-y-1">
              {missingFields.map((field) => (
                <li
                  key={field}
                  className="text-sm text-gray-700 dark:text-gray-300"
                >
                  • {field}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }
);

SchemaViewer.propTypes = {
  schema: PropTypes.object.isRequired,
  schemaData: PropTypes.object,
  completionPercentage: PropTypes.number,
  missingFields: PropTypes.array,
  onManualOverride: PropTypes.func.isRequired,
  confidenceLevels: PropTypes.object,
};

// ResultsDisplay Component
const ResultsDisplay = React.memo(
  ({ schema, schemaData = {}, connecting, onManualOverride }) =>
    !connecting &&
    schemaData && (
      <SchemaViewer
        schema={schema}
        schemaData={schemaData}
        completionPercentage={schemaData.completionPercentage || 0}
        missingFields={schemaData.missingFields || []}
        onManualOverride={onManualOverride}
        confidenceLevels={schemaData.confidenceLevels || {}}
      />
    )
);

ResultsDisplay.propTypes = {
  schema: PropTypes.object.isRequired,
  schemaData: PropTypes.object,
  connecting: PropTypes.bool.isRequired,
  onManualOverride: PropTypes.func.isRequired,
};

// ConnectionStatus Component
const ConnectionStatus = React.memo(
  ({ status = false, connecting = false }) => (
    <div className="flex items-center gap-2 mb-4">
      <div
        className={`w-2 h-2 rounded-full ${
          status
            ? 'bg-green-500'
            : connecting
            ? 'bg-yellow-500'
            : 'bg-red-500'
        }`}
      />
      <span className="text-sm text-gray-600 dark:text-gray-300">
        {status
          ? 'Connected'
          : connecting
          ? 'Connecting...'
          : 'Disconnected'}
      </span>
    </div>
  )
);

ConnectionStatus.propTypes = {
  status: PropTypes.bool,
  connecting: PropTypes.bool,
};

// HighlightedEmail Component
const HighlightedEmail = React.memo(
  ({ content = '', recognizedFields = {} }) => {
    const formattedContent =
      typeof content === 'string'
        ? content
        : JSON.stringify(content, null, 2);

    const highlightedContent = useMemo(() => {
      return formattedContent.split('\n').map((line, index) => {
        let highlightedLine = escapeRegExp(line);
        Object.keys(recognizedFields).forEach((field) => {
          const value = recognizedFields[field];
          if (value && highlightedLine.includes(value)) {
            const regex = new RegExp(`(${escapeRegExp(value)})`, 'g');
            highlightedLine = highlightedLine.replace(
              regex,
              `<span class="${getFieldColor(field)}">$1</span>`
            );
          }
        });
        return (
          <div key={`line-${index}-${line.substring(0, 10)}`}>
            <span dangerouslySetInnerHTML={{ __html: highlightedLine }} />
          </div>
        );
      });
    }, [formattedContent, recognizedFields]);

    return (
      <div className="font-mono whitespace-pre-wrap">
        {highlightedContent}
      </div>
    );
  }
);

HighlightedEmail.propTypes = {
  content: PropTypes.string,
  recognizedFields: PropTypes.object,
};

// ErrorBoundary Component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Log the error to an error reporting service if needed
    console.error('ErrorBoundary caught an error', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="mt-6 bg-red-50 dark:bg-red-100 border border-red-200 dark:border-red-400 rounded-lg p-4 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 dark:text-red-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <p className="text-sm text-red-700 dark:text-red-800">
              Something went wrong:
            </p>
            <pre className="text-sm text-red-700 dark:text-red-800 mt-1">
              {this.state.error.toString()}
            </pre>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Main EmailParser Component
function EmailParser() {
  const [parsing] = useState(false);
  const [state, dispatch] = useReducer(reducer, initialState);
  const {
    socket: { status: socketStatus, connecting },
    form: { email, schemaData },
    ui: { language, themeColors, isSettingsOpen, toasts },
    retryCount,
    missingFields,
    completionPercentage,
    recognizedFields,
    confidenceLevels,
    manualOverrides,
    error,
  } = state;

  const abortControllerRef = useRef(null);

  // Toast Manager
  const ToastManager = useMemo(
    () => ({
      add: (message, type) => {
        const id = Date.now();
        const toast = { id: `${id}-${Math.random()}`, message, type };
        dispatch({ type: 'ADD_TOAST', payload: toast });
        setTimeout(() => ToastManager.remove(toast.id), 3000);
      },
      remove: (id) => dispatch({ type: 'REMOVE_TOAST', payload: id }),
    }),
    [dispatch]
  );

  // Translations (Add actual translations as needed)
  const translations = useMemo(
    () => ({
      en: {
        // ...add English translations here...
      },
      es: {
        // ...add Spanish translations here...
      },
      // Add more languages as needed
    }),
    []
  );

  const t = useCallback(
    (key) => translations[language]?.[key] || key,
    [translations, language]
  );

  // Sample Email Templates
  const sampleEmails = useMemo(
    () => ({
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
    }),
    []
  );

  // Schema Definition
  const schema = useMemo(
    () => ({
      'Requesting Party': { Name: true, Contact: true, Address: false },
      'Insured Information': { Name: true, Contact: true, Address: true },
      'Adjuster Information': { Name: false, Contact: false, Email: false },
      'Assignment Information': {
        InsuranceCompany: true,
        ClaimNumber: true,
        DateOfLoss: true,
      },
      'Assignment Type': { Type: true, Details: false },
    }),
    []
  );

  // Highlight Patterns
  const highlightPatterns = useMemo(
    () => ({
      name: /Name:\s*(.*)/i,
      contact: /Contact:\s*(.*)/i,
      address: /Address:\s*(.*)/i,
      insuranceCompany: /Insurance Company:\s*(.*)/i,
      claimNumber: /Claim Number:\s*(.*)/i,
      dateOfLoss: /Date of Loss:\s*(.*)/i,
      type: /Subject:\s*(.*)/i,
      details: /Please inspect (.*)\./i,
    }),
    []
  );

  // Field Detector
  const fieldDetector = useMemo(
    () => ({
      patterns: highlightPatterns,
      detect: (text, type) =>
        text.match(highlightPatterns[type])?.[1],
    }),
    [highlightPatterns]
  );

  // Toggle Theme using ThemeManager
  const toggleTheme = useCallback(() => {
    themeManager.toggleTheme(); // Use the centralized ThemeManager
    ToastManager.add('Theme updated', 'success');
  }, [ToastManager]);

  // Initialize Theme on Mount
  useEffect(() => {
    themeManager.initialize(); // Initialize theme on mount
  }, []);

  // Handle Errors
  const handleError = useCallback(
    (error, context) => {
      dispatch({ type: 'SET_ERROR', payload: error.message });
      ToastManager.add(
        context ? `${context}: ${error.message}` : error.message,
        'error'
      );
    },
    [ToastManager]
  );

  // Socket Connection Management
  useEffect(() => {
    const socket = socketManager.getSocket();
    let mounted = true;

    if (socket) {
      const handleConnect = () => {
        if (mounted) {
          dispatch({
            type: 'UPDATE_SOCKET_STATUS',
            payload: { status: true, connecting: false },
          });
        }
      };

      const handleDisconnect = () => {
        if (mounted) {
          dispatch({
            type: 'UPDATE_SOCKET_STATUS',
            payload: { status: false, connecting: false },
          });
        }
      };

      socket.on('connect', handleConnect);
      socket.on('disconnect', handleDisconnect);

      // Set initial status
      dispatch({
        type: 'UPDATE_SOCKET_STATUS',
        payload: {
          status: socket.connected,
          connecting: !socket.connected,
        },
      });

      return () => {
        mounted = false;
        socket.off('connect', handleConnect);
        socket.off('disconnect', handleDisconnect);
      };
    }
  }, []);

  // Initialize Language and Theme from localStorage on Mount
  useEffect(() => {
    const savedLanguage = localStorage.getItem('language');
    const savedTheme = localStorage.getItem('themeColors');
    if (savedLanguage) {
      dispatch({ type: 'SET_LANGUAGE', payload: savedLanguage });
    }
    if (savedTheme) {
      dispatch({
        type: 'SET_THEME_COLORS',
        payload: JSON.parse(savedTheme),
      });
    }
  }, []);

  // Auto-save to localStorage
  useEffect(() => {
    if (language) localStorage.setItem('language', language);
    if (themeColors)
      localStorage.setItem(
        'themeColors',
        JSON.stringify(themeColors)
      );
  }, [language, themeColors]);

  // Update CSS Variables for Theme Colors
  useEffect(() => {
    document.documentElement.style.setProperty(
      '--color-primary',
      themeColors.primary
    );
    document.documentElement.style.setProperty(
      '--color-secondary',
      themeColors.secondary
    );
  }, [themeColors]);

  // Handle System Dark Mode Preference
  useEffect(() => {
    const mediaQuery = window.matchMedia(
      '(prefers-color-scheme: dark)'
    );
    const handler = (e) => {
      if (
        (e.matches && themeManager.currentTheme !== 'dark') ||
        (!e.matches && themeManager.currentTheme !== 'light')
      ) {
        toggleTheme();
      }
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [toggleTheme]);

  // Debug Log email Before Rendering
  useEffect(() => {
    console.log("Email content type:", typeof email);
    console.log("Email content value:", email);
  }, [email]);

  // Toast Notifications
  const renderToasts = useMemo(
    () => (
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-center p-4 rounded-lg shadow-lg ${
              toast.type === 'success'
                ? 'bg-green-100 dark:bg-green-700'
                : toast.type === 'error'
                ? 'bg-red-100 dark:bg-red-700'
                : 'bg-blue-100 dark:bg-blue-700'
            }`}
          >
            <div className="flex-1 text-sm text-gray-800 dark:text-gray-100">
              {toast.message}
            </div>
            <button
              onClick={() => ToastManager.remove(toast.id)}
            >
              <X className="w-4 h-4 text-gray-600 dark:text-gray-200" />
            </button>
          </div>
        ))}
      </div>
    ),
    [toasts, ToastManager]
  );

  // Handle Submit
  const handleSubmit = useCallback(
    (e) => {
      if (e) e.preventDefault();
      dispatch({
        type: 'START_PARSING',
      });

      // Validate form before submission
      const validationError = validateEmailContent(email);
      if (validationError) {
        handleError(new Error(validationError), 'Validation');
        dispatch({
          type: 'STOP_PARSING',
          payload: { progress: 0, error: validationError },
        });
        return;
      }

      // Cancel any in-flight requests
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      const socket = socketManager.getSocket();
      if (!socket || !socketStatus) {
        handleError(
          new Error('Socket is not connected'),
          'Connection'
        );
        dispatch({
          type: 'STOP_PARSING',
          payload: { progress: 0, error: 'Socket is not connected' },
        });
        return;
      }

      // Emit parseEmail event with necessary data
      socket.emit(
        'parseEmail',
        { emailContent: email, parserOption: 'enhanced' },
        (response) => {
          console.log('Server response:', response);
          if (response.error) {
            handleError(new Error(response.error), 'Parsing');
            if (retryCount < 3) {
              dispatch({ type: 'INCREMENT_RETRY' });
              ToastManager.add(
                `Retrying... (${retryCount + 1})`,
                'error'
              );
              setTimeout(() => {
                handleSubmit(e);
              }, 1000);
            } else {
              ToastManager.add(
                'Failed to parse email after multiple attempts.',
                'error'
              );
            }
            dispatch({
              type: 'STOP_PARSING',
              payload: { progress: 0, error: response.error },
            });
          } else {
            // Ensure recognizedFields are strings
            const processedRecognizedFields = Object.fromEntries(
              Object.entries(response.recognizedFields || {}).map(
                ([key, val]) => [key, typeof val === 'string' ? val : JSON.stringify(val)]
              )
            );

            const mappedData = mapToSchema(
              response.data,
              schema,
              manualOverrides
            );
            const completion = calculateCompletion(
              mappedData,
              schema
            );
            const missing = identifyMissingFields(
              mappedData,
              schema
            );
            dispatch({
              type: 'SET_SCHEMA_DATA',
              payload: {
                schemaData: mappedData,
                recognizedFields: processedRecognizedFields,
                confidenceLevels:
                  response.confidenceLevels || {},
              },
            });
            dispatch({ type: 'SET_COMPLETION', payload: completion });
            dispatch({ type: 'SET_MISSING_FIELDS', payload: missing });
            ToastManager.add('Email parsed successfully', 'success');
            dispatch({ type: 'RESET_RETRY' });
            dispatch({
              type: 'STOP_PARSING',
              payload: { progress: 100, error: null },
            });
          }
        }
      );
    },
    [
      email,
      socketStatus,
      handleError,
      ToastManager,
      retryCount,
      schema,
      manualOverrides,
    ]
  );

  // Handle Sample Email Loading
  const handleSampleEmail = useCallback(
    (type = 'complete') => {
      const sample = sampleEmails[type];
      if (sample && typeof sample === 'string') {
        dispatch({ type: 'SET_EMAIL', payload: sample });
        ToastManager.add('Sample email loaded', 'success');
      } else {
        ToastManager.add('Sample email type not found', 'error');
      }
    },
    [sampleEmails, ToastManager]
  );

  // Copy to Clipboard
  const copyToClipboard = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(
        JSON.stringify(schemaData, null, 2)
      );
      ToastManager.add('Copied to clipboard', 'success');
    } catch (err) {
      ToastManager.add('Failed to copy', 'error');
    }
  }, [schemaData, ToastManager]);

  // Save as JSON
  const saveAsJSON = useCallback(() => {
    const blob = new Blob(
      [JSON.stringify(schemaData, null, 2)],
      { type: 'application/json' }
    );
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
  const handleManualOverride = useCallback(
    (section, field, value) => {
      if (value && typeof value === 'string') {
        dispatch({
          type: 'SET_MANUAL_OVERRIDE',
          payload: { [`${section}.${field}`]: value },
        });
        ToastManager.add(`Overridden ${field}`, 'success');
      }
    },
    [ToastManager]
  );

  // Key Down Handler
  const handleKeyDown = useCallback(
    (e) => {
      if (e.ctrlKey && e.key === 'Enter') {
        handleSubmit(e);
      }
      if (e.key === 'Escape') {
        dispatch({ type: 'CLEAR_EMAIL' });
        ToastManager.add('Input cleared', 'success');
      }
    },
    [handleSubmit, ToastManager]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () =>
      window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Cleanup Configuration
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      dispatch({ type: 'RESET_STATE' });
    };
  }, []);

  // Render Settings Modal
  const renderSettingsModal = useMemo(
    () =>
      isSettingsOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg w-11/12 max-w-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Theme Settings
              </h2>
              <button
                onClick={() => dispatch({ type: 'CLOSE_SETTINGS' })}
              >
                <X className="w-5 h-5 text-gray-600 dark:text-gray-200" />
              </button>
            </div>
            <form className="space-y-4">
              <div>
                <label
                  htmlFor="language"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Language
                </label>
                <select
                  id="language"
                  value={language}
                  onChange={(e) =>
                    dispatch({
                      type: 'SET_LANGUAGE',
                      payload: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="en">English</option>
                  <option value="es">Español</option>
                  {/* Add more languages here */}
                </select>
              </div>
              <div>
                <label
                  htmlFor="primaryColor"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Primary Color
                </label>
                <input
                  type="color"
                  id="primaryColor"
                  value={themeColors.primary}
                  onChange={(e) =>
                    dispatch({
                      type: 'SET_THEME_COLORS',
                      payload: {
                        ...themeColors,
                        primary: e.target.value,
                      },
                    })
                  }
                  className="w-full h-10 p-0 border-none"
                />
              </div>
              <div>
                <label
                  htmlFor="secondaryColor"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Secondary Color
                </label>
                <input
                  type="color"
                  id="secondaryColor"
                  value={themeColors.secondary}
                  onChange={(e) =>
                    dispatch({
                      type: 'SET_THEME_COLORS',
                      payload: {
                        ...themeColors,
                        secondary: e.target.value,
                      },
                    })
                  }
                  className="w-full h-10 p-0 border-none"
                />
              </div>
            </form>
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => dispatch({ type: 'CLOSE_SETTINGS' })}
                className="px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ),
    [isSettingsOpen, language, themeColors, dispatch]
  );

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Toast Notifications */}
        {renderToasts}

        {/* Settings Modal */}
        {renderSettingsModal}

        <div className="max-w-6xl mx-auto py-8 px-4">
          {/* Top Controls */}
          <div className="flex justify-between items-center mb-4">
            <div className="flex space-x-2">
              {/* Sample Email Buttons */}
              {[
                { type: 'complete', label: '1' },
                { type: 'partial', label: '2' },
                { type: 'differentType', label: '3' },
              ].map(({ type, label }) => (
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
                onClick={() => dispatch({ type: 'OPEN_SETTINGS' })}
                className="flex items-center text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white focus:outline-none"
                title="Theme Settings"
              >
                <Settings className="w-5 h-5 mr-1" />
                Settings
              </button>
              <button
                onClick={toggleTheme}
                className="flex items-center text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white focus:outline-none"
                title="Toggle Dark Mode"
              >
                {themeManager.currentTheme === 'dark' ? (
                  <>
                    <Sun className="w-5 h-5 mr-1" />
                    Light Mode
                  </>
                ) : (
                  <>
                    <Moon className="w-5 h-5 mr-1" />
                    Dark Mode
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Connection Status */}
          <ConnectionStatus
            status={socketStatus}
            connecting={connecting}
          />

          {/* Header */}
          <div className="flex items-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              Email Parser
            </h1>
          </div>

          {/* Main Form */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="emailContent"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Email Content
                </label>
                <textarea
                  id="emailContent"
                  value={email}
                  onChange={(e) =>
                    dispatch({
                      type: 'SET_EMAIL',
                      payload: e.target.value,
                    })
                  }
                  className="w-full h-64 px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 overflow-auto font-mono"
                  placeholder="Email Content"
                  spellCheck="false"
                />
                <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Characters: {email.length}
                </div>
              </div>

              {/* Progress Bar */}
              {completionPercentage > 0 && (
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-4">
                  <div
                    className="bg-blue-600 dark:bg-blue-500 h-2.5 rounded-full"
                    style={{ width: `${completionPercentage}%` }}
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={
                  state.parsing.active ||
                  !email.trim() ||
                  !socketStatus
                }
                className={`w-full bg-blue-600 dark:bg-blue-500 text-white h-12 px-6 rounded-lg font-medium
                         hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 
                         focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed
                         flex items-center justify-center`}
              >
                {state.parsing.active ? (
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
                <p className="text-sm text-red-700 dark:text-red-800">
                  Error:
                </p>
                <pre className="text-sm text-red-700 dark:text-red-800 mt-1">
                  {error}
                </pre>
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
                <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Smart Highlighting
                </h2>
                <HighlightedEmail
                  content={email}
                  recognizedFields={recognizedFields}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
}

EmailParser.propTypes = {};

// Export the EmailParser Component
export default EmailParser;
