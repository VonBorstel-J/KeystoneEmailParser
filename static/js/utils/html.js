// static/js/utils/html.js

// Escapes HTML characters to prevent XSS
export const escapeHtml = (unsafe) => {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
};

// Escapes special characters in regex
export const escapeRegExp = (string) => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
};

// Converts parsed data into human-readable HTML
export const renderHumanReadable = (data) => {
  // Implement your logic to convert parsed data into human-readable HTML
  // Example:
  let html = '<ul>';
  for (const [key, value] of Object.entries(data)) {
    if (typeof value === 'object' && value !== null) {
      html += `<li><strong>${capitalize(key)}:</strong> <ul>`;
      for (const [subKey, subValue] of Object.entries(value)) {
        html += `<li><strong>${capitalize(subKey)}:</strong> ${escapeHtml(String(subValue))}</li>`;
      }
      html += '</ul></li>';
    } else {
      html += `<li><strong>${capitalize(key)}:</strong> ${escapeHtml(String(value))}</li>`;
    }
  }
  html += '</ul>';
  return html;
};

// Highlights parsed sections within the original email content
export const highlightEmailContent = (emailContent, parsedData) => {
  let highlightedContent = escapeHtml(emailContent);

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
};

// Capitalizes the first letter of a string
const capitalize = (s) => {
  if (typeof s !== 'string') return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
};
