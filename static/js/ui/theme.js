// static/js/ui/theme.js

class ThemeManager {
    constructor() {
      this.currentTheme = localStorage.getItem("theme") || "light";
      this.applyTheme(this.currentTheme);
      this.toggleButton = document.getElementById("theme-toggle");
      this.init();
    }
  
    init() {
      if (this.toggleButton) {
        this.toggleButton.addEventListener("click", () => this.toggleTheme());
      }
    }
  
    toggleTheme() {
      this.currentTheme = this.currentTheme === "light" ? "dark" : "light";
      this.applyTheme(this.currentTheme);
      localStorage.setItem("theme", this.currentTheme);
    }
  
    applyTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      this.updateThemeIcon(theme);
    }
  
    updateThemeIcon(theme) {
      const themeIcon = document.getElementById("theme-icon");
      if (themeIcon) {
        themeIcon.textContent = theme === "light" ? "🌙" : "☀️";
      }
    }
  }
  
  const themeManager = new ThemeManager();
  export default themeManager;
  