// static/js/main.js
import React from 'react';
import ReactDOM from 'react-dom';
import socketManager from './core/socket.js';
import Parser from './core/parser.js';
import ValidationManager from './core/validation.js';
import Toast from '../components/common/Toast.jsx';
import Modal from '../components/common/Modal.jsx';
import themeManager from './ui/theme.js';
import ParsingOverlay from '../components/ParsingOverlay/index.jsx';
import { formatJSON, toCSV } from './utils/format.js';
import { getElement, createElement, debounce } from './utils/dom.js';
import { setSocketConnected, setSocketDisconnected, setSocketError } from './actions/socketActions.js';
import socketReducer from './reducers/socketReducer.js';
import { escapeHtml, renderHumanReadable, capitalize, escapeRegExp } from './utils/html.js';

// Initialize Socket Manager
const socket = socketManager.getSocket();

// Initialize Parser
const parser = new Parser(socket);

// Initialize Theme Manager
themeManager.initialize();

// Initialize React Components
initializeReactComponents();

// Initialize Event Listeners
initializeEventListeners();

// State to control the visibility of the ParsingOverlay
let isOverlayActive = false;

// State to store parsed entries for download
const parsedEntries = [];

// Initialize React Components by mounting them to designated DOM elements
function initializeReactComponents() {
  const parsingOverlayRoot = getElement('parsingOverlayRoot');
  if (parsingOverlayRoot) {
    ReactDOM.render(
      <ParsingOverlay
        socket={socket}
        active={isOverlayActive}
        emailContent={getElement('email_content') ? getElement('email_content').value : ''}
        onClose={handleOverlayClose}
      />,
      parsingOverlayRoot
    );
  }
}

// Handles the closure of the ParsingOverlay
function handleOverlayClose() {
  isOverlayActive = false;
  updateParsingOverlay();
}

// Updates the ParsingOverlay component with the current state
function updateParsingOverlay() {
  const parsingOverlayRoot = getElement('parsingOverlayRoot');
  if (parsingOverlayRoot) {
    ReactDOM.render(
      <ParsingOverlay
        socket={socket}
        active={isOverlayActive}
        emailContent={getElement('email_content') ? getElement('email_content').value : ''}
        onClose={handleOverlayClose}
      />,
      parsingOverlayRoot
    );
  }
}

// Initializes Event Listeners for form submission and other interactions
function initializeEventListeners() {
  const parserForm = getElement('parserForm');
  if (parserForm) {
    parserForm.addEventListener('submit', handleFormSubmission);
  }

  const sampleButtons = document.querySelectorAll('.sample-btn');
  sampleButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const templateName = button.getAttribute('data-template');
      loadSampleEmail(templateName);
    });
  });

  const emailContent = getElement('email_content');
  if (emailContent) {
    emailContent.addEventListener('input', debounce(updateCharCount, 300));
  }

  const themeToggle = getElement('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }

  const downloadCsvBtn = getElement('downloadCsvBtn');
  if (downloadCsvBtn) {
    downloadCsvBtn.addEventListener('click', downloadCSV);
  }

  const downloadPdfBtn = getElement('downloadPdfBtn');
  if (downloadPdfBtn) {
    downloadPdfBtn.addEventListener('click', downloadPDF);
  }

  const copyResultsBtn = getElement('copyResultsBtn');
  if (copyResultsBtn) {
    copyResultsBtn.addEventListener('click', copyResults);
  }

  const helpButton = getElement('help-button');
  const helpModal = getElement('helpModal');
  const closeHelpBtn = getElement('closeHelpBtn');

  if (helpButton && helpModal && closeHelpBtn) {
    helpButton.addEventListener('click', () => {
      openHelpModal(helpModal);
    });

    closeHelpBtn.addEventListener('click', () => {
      closeHelpModal(helpModal);
    });
  }

  const documentImageInput = getElement('document_image');
  if (documentImageInput) {
    documentImageInput.addEventListener('change', handleFileUpload);
  }
}

// Handles the form submission for parsing emails
async function handleFormSubmission(e) {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);
  const parserOption = formData.get('parser_option');
  const emailContent = formData.get('email_content').trim();
  const documentImage = formData.get('document_image');

  // Validate Email Content
  const emailErrors = ValidationManager.validate('emailContent', emailContent);
  if (emailErrors.length > 0) {
    toggleInvalidState(getElement('email_content'), true);
    showValidationError('email_content_error', emailErrors);
    showToast('error', emailErrors.join(' '));
    return;
  } else {
    toggleInvalidState(getElement('email_content'), false);
    hideValidationError('email_content_error');
  }

  // Validate Parser Option
  const parserErrors = ValidationManager.validate('parserOption', parserOption);
  if (parserErrors.length > 0) {
    toggleInvalidState(getElement('parser_option'), true);
    showValidationError('parser_option_error', parserErrors);
    showToast('error', parserErrors.join(' '));
    return;
  } else {
    toggleInvalidState(getElement('parser_option'), false);
    hideValidationError('parser_option_error');
  }

  // Validate Document Image (if provided)
  if (documentImage && documentImage.size > 0) {
    const imageErrors = ValidationManager.validate('documentImage', documentImage);
    if (imageErrors.length > 0) {
      toggleInvalidState(getElement('document_image'), true);
      showValidationError('document_image_error', imageErrors);
      showToast('error', imageErrors.join(' '));
      return;
    } else {
      toggleInvalidState(getElement('document_image'), false);
      hideValidationError('document_image_error');
    }
  } else {
    toggleInvalidState(getElement('document_image'), false);
    hideValidationError('document_image_error');
  }

  // Ensure socketId is available
  const socketId = socket.id;
  if (!socketId) {
    showToast('error', 'Socket connection not established. Please wait and try again.');
    return;
  }

  // Append socket_id to formData
  formData.append('socket_id', socketId);
  console.log('Socket ID being sent:', socketId);

  // Activate the ParsingOverlay
  isOverlayActive = true;
  updateParsingOverlay();

  try {
    const response = await parser.parseEmail(formData);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error_message || 'An error occurred while parsing.');
    }
    showToast('success', data.message);
    // Parsing progress and completion are handled via Socket.IO events and ParsingOverlay
  } catch (error) {
    console.error('Error during parsing:', error);
    showToast('error', error.message);
    hideLoadingOverlay();
    hideDownloadButtons();
    isOverlayActive = false;
    updateParsingOverlay();
  }
}

// Displays validation errors for a specific field
function showValidationError(elementId, errors) {
  const errorElement = getElement(elementId);
  if (errorElement) {
    errorElement.textContent = errors.join(', ');
    errorElement.classList.remove('hidden');
  }
}

// Hides validation errors for a specific field
function hideValidationError(elementId) {
  const errorElement = getElement(elementId);
  if (errorElement) {
    errorElement.textContent = '';
    errorElement.classList.add('hidden');
  }
}

// Toggles the invalid state of a form input
function toggleInvalidState(element, isInvalid) {
  if (element) {
    if (isInvalid) {
      element.classList.add('is-invalid');
    } else {
      element.classList.remove('is-invalid');
    }
  }
}

// Updates the character count display
function updateCharCount() {
  const emailContent = getElement('email_content');
  const charCount = getElement('char_count');
  if (emailContent && charCount) {
    const count = emailContent.value.length;
    charCount.textContent = `${count} character${count !== 1 ? 's' : ''}`;
    charCount.className = count > 5000 ? 'text-red-500' : 'text-gray-500';
  }
}

// Loads a sample email based on the provided template name
function loadSampleEmail(templateName) {
  if (EMAIL_TEMPLATES[templateName]) {
    const emailContent = getElement('email_content');
    if (emailContent) {
      emailContent.value = EMAIL_TEMPLATES[templateName];
      updateCharCount();
    }
  }
}

// Copies the JSON parsed results to the clipboard
function copyResults() {
  const jsonOutput = getElement('jsonOutput');
  if (jsonOutput) {
    navigator.clipboard
      .writeText(jsonOutput.textContent)
      .then(() => {
        showToast('success', 'Parsed data copied to clipboard!');
      })
      .catch(() => {
        showToast('error', 'Failed to copy to clipboard.');
      });
  }
}

// Displays the parsed data in both JSON and Human-Readable formats
function displayParsedData(parsedData) {
  // Display JSON Output
  const jsonOutput = getElement('jsonOutput');
  if (jsonOutput) {
    const prettyJson = JSON.stringify(parsedData, null, 2);
    jsonOutput.textContent = prettyJson;
    Prism.highlightElement(jsonOutput);
  }

  // Display Human-Readable Output
  const humanOutput = getElement('humanOutput');
  if (humanOutput) {
    humanOutput.innerHTML = renderHumanReadable(parsedData);
  }

  // Display Original Email with Highlights
  const originalEmail = getElement('originalEmail');
  const emailContent = getElement('email_content') ? getElement('email_content').value : '';
  if (originalEmail && emailContent) {
    originalEmail.innerHTML = highlightEmailContent(emailContent, parsedData);
  }

  // Store parsed entries for download
  parsedEntries.push(flattenParsedData(parsedData));

  // Show Download Buttons
  const downloadCsvBtn = getElement('downloadCsvBtn');
  const downloadPdfBtn = getElement('downloadPdfBtn');
  if (downloadCsvBtn && downloadPdfBtn) {
    downloadCsvBtn.classList.remove('hidden');
    downloadPdfBtn.classList.remove('hidden');
  }
}

// Flattens nested parsed data for CSV export
function flattenParsedData(data) {
  const flatData = {};
  for (const [section, content] of Object.entries(data)) {
    if (typeof content === 'object' && content !== null) {
      for (const [key, value] of Object.entries(content)) {
        flatData[`${capitalize(section)} - ${capitalize(key)}`] = value;
      }
    } else {
      flatData[capitalize(section)] = content;
    }
  }
  return flatData;
}

// Highlights the original email content based on parsed sections
function highlightEmailContent(emailContent, parsedData) {
  let highlightedContent = emailContent;

  for (const [section, content] of Object.entries(parsedData)) {
    if (section === 'validation_issues') continue;
    if (typeof content === 'object' && content !== null) {
      for (const [key, value] of Object.entries(content)) {
        if (typeof value === 'string' && value.trim() !== '') {
          const regex = new RegExp(`(${escapeRegExp(value)})`, 'g');
          highlightedContent = highlightedContent.replace(
            regex,
            `<span class="highlight-${section.replace(/\s+/g, '')}">${escapeHtml(value)}</span>`
          );
        }
      }
    }
  }

  return highlightedContent;
}

// Downloads the parsed data as a CSV file
function downloadCSV() {
  if (parsedEntries.length === 0) {
    showToast('error', 'No parsed data available to download.');
    return;
  }

  const headers = Object.keys(parsedEntries[parsedEntries.length - 1]);
  const csvContent = [
    headers.join(','),
    ...parsedEntries.map((entry) =>
      headers
        .map((header) => {
          let cell = entry[header];
          if (typeof cell === 'object' && cell !== null) {
            cell = JSON.stringify(cell);
          }
          cell = String(cell).replace(/"/g, '""');
          return /[",\n]/.test(cell) ? `"${cell}"` : cell;
        })
        .join(',')
    ),
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  const timestamp = new Date().toISOString().replace(/[:\-T.]/g, '').split('Z')[0];
  link.setAttribute('download', `parsed_emails_${timestamp}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  showToast('success', 'CSV downloaded successfully!');
}

// Downloads the parsed data as a PDF file
async function downloadPDF() {
  if (parsedEntries.length === 0) {
    showToast('error', 'No parsed data available to download.');
    return;
  }

  if (!window.jspdf || !window.jspdf.jsPDF) {
    showToast('error', 'PDF library not loaded.');
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();

  // Add title
  doc.setFontSize(16);
  doc.text('Parsed Email Data', 10, 10);

  // Add JSON data
  doc.setFontSize(12);
  const jsonString = JSON.stringify(parsedEntries[parsedEntries.length - 1], null, 2);
  const lines = doc.splitTextToSize(jsonString, 180);
  doc.text(lines, 10, 20);

  // Save the PDF
  doc.save(`parsed_emails_${new Date().toISOString().split('T')[0]}.pdf`);

  showToast('success', 'PDF downloaded successfully!');
}

// Handles file upload validation and preview (if needed)
function handleFileUpload(e) {
  const file = e.target.files[0];
  if (file) {
    console.log('File uploaded:', file.name);
    // Add file preview functionality here if needed
  }
}

// Shows a toast notification
function showToast(type, message) {
  let toastContainer = getElement('toast-container');
  if (!toastContainer) {
    toastContainer = createElement('div', {
      id: 'toast-container',
      className: 'fixed top-4 right-4 flex flex-col items-end space-y-2 z-50',
      role: 'alert',
      'aria-live': 'assertive',
    });
    document.body.appendChild(toastContainer);
  }

  const toast = createElement('div', {
    className: `toast ${type === 'success' ? 'toast-success' : 'toast-error'} bg-${type === 'success' ? 'green' : 'red'}-100 border-l-4 border-${type === 'success' ? 'green' : 'red'}-500 text-${type === 'success' ? 'green' : 'red'}-700 p-4 rounded-md shadow-lg flex items-center`,
    innerHTML: `
      <div class="flex-shrink-0">
        ${type === 'success' ? `
          <svg class="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        ` : `
          <svg class="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        `}
      </div>
      <div class="ml-3">
        <p class="text-sm">${message}</p>
      </div>
      <button class="ml-auto bg-transparent border-0 text-current hover:text-gray-700" aria-label="Close">
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    `,
  });

  toast.querySelector('button').addEventListener('click', () => {
    toast.remove();
  });

  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 5000);
}

// Toggles between light and dark themes (handled by themeManager)
function toggleTheme() {
  themeManager.toggleTheme();
}

// Opens the Help Modal
function openHelpModal(modal) {
  if (modal) {
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    modal.querySelector('h3')?.focus();
  }
}

// Closes the Help Modal
function closeHelpModal(modal) {
  if (modal) {
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    getElement('help-button')?.focus();
  }
}

// Hides the download buttons
function hideDownloadButtons() {
  const downloadCsvBtn = getElement('downloadCsvBtn');
  const downloadPdfBtn = getElement('downloadPdfBtn');
  if (downloadCsvBtn && downloadPdfBtn) {
    downloadCsvBtn.classList.add('hidden');
    downloadPdfBtn.classList.add('hidden');
  }
}

// Ensure that `loadingAnimation` is defined if you're using it
let loadingAnimation;
document.addEventListener('DOMContentLoaded', () => {
  const loadingAnimationContainer = getElement('loadingOverlay');
  if (loadingAnimationContainer) {
    loadingAnimation = lottie.loadAnimation({
      container: loadingAnimationContainer.querySelector('.relative.w-32.h-32'),
      renderer: 'svg',
      loop: true,
      autoplay: false,
      path: '/path/to/loading.json',
    });
  }
});

// Define your email templates here
const EMAIL_TEMPLATES = {
  claim: `Dear Sir/Madam,

I am writing to formally file a claim regarding...`,
  informal_claim: `Hi there,

I need to file a claim because...`,
  formal_fire_claim: `To Whom It May Concern,

I regret to inform you that...`,
};
