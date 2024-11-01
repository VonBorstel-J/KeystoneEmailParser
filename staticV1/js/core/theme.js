class ThemeManager {
  constructor() {
    // Initialize currentTheme from localStorage or default to 'light'
    this.currentTheme = localStorage.getItem('theme') || 'light';
  }

  // Initializes the theme on app load
  initialize() {
    this.applyTheme(this.currentTheme); // Apply the initial theme
  }

  // Applies the theme by setting the data attribute
  applyTheme(theme) {
    // Set the theme attribute on the HTML element
    document.documentElement.setAttribute('data-theme', theme);
    this.currentTheme = theme;
    localStorage.setItem('theme', theme); // Persist the theme in localStorage
  }

  // Toggles between light and dark themes
  toggleTheme() {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    this.applyTheme(newTheme); // Apply the new theme
  }
}

// Singleton instance of ThemeManager
const themeManager = new ThemeManager();
export default themeManager;
