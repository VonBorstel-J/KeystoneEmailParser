// static/js/utils/html.js
export const escapeHtml = (text) => {
    if (typeof text !== 'string') return '';
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return text.replace(/[&<>"']/g, m => map[m]);
  };
  
  export const renderHumanReadable = (data) => {
    if (typeof data !== 'object') return '';
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
  };
  
  export const capitalize = (str) => typeof str === 'string' ? str.charAt(0).toUpperCase() + str.slice(1) : '';
  
  export const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  