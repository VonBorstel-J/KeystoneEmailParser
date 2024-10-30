// static/js/actions/themeActions.js
import { TOGGLE_THEME, SET_THEME } from './actionTypes.js';

export const toggleTheme = () => ({
  type: TOGGLE_THEME,
});

export const setTheme = (theme) => ({
  type: SET_THEME,
  payload: theme,
});
