// static/js/reducers/themeReducer.js
import { TOGGLE_THEME, SET_THEME } from '@actions/actionTypes.js';

const initialState = {
  currentTheme: 'light',
};

const themeReducer = (state = initialState, action) => {
  switch (action.type) {
    case TOGGLE_THEME:
      const newTheme = state.currentTheme === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', newTheme);
      document.documentElement.classList.remove(state.currentTheme);
      document.documentElement.classList.add(newTheme);
      return {
        ...state,
        currentTheme: newTheme,
      };
    case SET_THEME:
      document.documentElement.classList.remove(state.currentTheme);
      document.documentElement.classList.add(action.payload);
      return {
        ...state,
        currentTheme: action.payload,
      };
    default:
      return state;
  }
};

export default themeReducer;
