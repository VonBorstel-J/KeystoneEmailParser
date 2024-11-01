// tailwind.config.js
module.exports = {
  content: ['./frontend/**/*.{js,jsx,ts,tsx}', './templates/**/*.html'],
  darkMode: 'media', // Supports system preference for dark mode
  theme: {
    extend: {
      colors: {
        primary: {
          light: '#63b3ed',
          DEFAULT: '#3182ce',
          dark: '#2c5282',
        },
        secondary: {
          light: '#fbd38d',
          DEFAULT: '#ed8936',
          dark: '#c05621',
        },
      },
      spacing: {
        18: '4.5rem', // Custom spacing value for more flexibility
      },
      borderRadius: {
        'xl': '1.25rem', // Extends border radius options for rounded corners
      },
      boxShadow: {
        'custom-light': '0 4px 6px rgba(0, 0, 0, 0.1)',
        'custom-dark': '0 8px 12px rgba(0, 0, 0, 0.3)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'), // Adds better form styles out of the box
    require('@tailwindcss/typography'), // Adds utilities for improving typography
  ],
};
