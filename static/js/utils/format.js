// static/js/utils/format.js

export const formatJSON = (data) => {
  if (typeof data !== 'object') throw new TypeError('formatJSON expects an object');
  try {
    return JSON.stringify(data, null, 2);
  } catch (error) {
    console.error('formatJSON error:', error);
    throw error;
  }
};

export const toCSV = (data) => {
  if (!Array.isArray(data)) throw new TypeError('toCSV expects an array');
  if (data.length === 0) return '';
  try {
    const headers = Object.keys(data[0]);
    const csvRows = [
      headers.join(','),
      ...data.map(row => headers.map(field => {
        let cell = row[field];
        if (typeof cell === 'object' && cell !== null) cell = JSON.stringify(cell);
        cell = String(cell).replace(/"/g, '""');
        return /[",\n]/.test(cell) ? `"${cell}"` : cell;
      }).join(','))
    ];
    return csvRows.join('\n');
  } catch (error) {
    console.error('toCSV error:', error);
    throw error;
  }
};

export const toHumanReadable = (data) => {
  if (typeof data !== 'object') throw new TypeError('toHumanReadable expects an object');
  try {
    let html = '<div class="human-readable-container"><div class="accordion" id="parsedDataAccordion">';
    let index = 0;
    for (const [section, content] of Object.entries(data)) {
      if (section === "validation_issues") continue;
      const collapseId = `collapseSection${index}`;
      html += `
        <div class="accordion-item">
          <h2 class="accordion-header" id="heading${index}">
            <button class="accordion-button ${index !== 0 ? "collapsed" : ""}" type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="${index === 0}" aria-controls="${collapseId}">
              ${capitalize(section)}
            </button>
          </h2>
          <div id="${collapseId}" class="accordion-collapse collapse ${index === 0 ? "show" : ""}" aria-labelledby="heading${index}" data-bs-parent="#parsedDataAccordion">
            <div class="accordion-body">
      `;
      if (typeof content === "object" && content !== null) {
        html += "<ul>";
        for (const [key, value] of Object.entries(content)) {
          html += `<li><strong>${capitalize(key)}:</strong> ${escapeHtml(value)}</li>`;
        }
        html += "</ul>";
      } else {
        html += `<p>${escapeHtml(content)}</p>`;
      }
      html += `
            </div>
          </div>
        </div>
      `;
      index++;
    }
    html += "</div></div>";
    return html;
  } catch (error) {
    console.error('toHumanReadable error:', error);
    throw error;
  }
};

const capitalize = (str) => typeof str === 'string' ? str.charAt(0).toUpperCase() + str.slice(1) : '';

const escapeHtml = (text) => {
  if (typeof text !== 'string') return '';
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return text.replace(/[&<>"']/g, m => map[m]);
};
