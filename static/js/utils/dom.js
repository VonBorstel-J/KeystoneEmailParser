// static/js/utils/dom.js
export const addClass = (element, className) => {
  if (!(element instanceof HTMLElement)) throw new TypeError('addClass expects an HTMLElement');
  if (typeof className !== 'string') throw new TypeError('className must be a string');
  element.classList.add(className);
};

export const removeClass = (element, className) => {
  if (!(element instanceof HTMLElement)) throw new TypeError('removeClass expects an HTMLElement');
  if (typeof className !== 'string') throw new TypeError('className must be a string');
  element.classList.remove(className);
};

export const toggleClass = (element, className) => {
  if (!(element instanceof HTMLElement)) throw new TypeError('toggleClass expects an HTMLElement');
  if (typeof className !== 'string') throw new TypeError('className must be a string');
  element.classList.toggle(className);
};

export const hasClass = (element, className) => {
  if (!(element instanceof HTMLElement)) throw new TypeError('hasClass expects an HTMLElement');
  if (typeof className !== 'string') throw new TypeError('className must be a string');
  return element.classList.contains(className);
};

export const setInnerHTML = (element, html) => {
  if (!(element instanceof HTMLElement)) throw new TypeError('setInnerHTML expects an HTMLElement');
  if (typeof html !== 'string') throw new TypeError('html must be a string');
  element.innerHTML = html;
};

export const getInputValue = (id) => {
  if (typeof id !== 'string') throw new TypeError('getInputValue expects a string ID');
  const element = document.getElementById(id);
  if (!(element instanceof HTMLInputElement)) throw new TypeError('Element is not an input');
  return element.value;
};

export const getFile = (id) => {
  if (typeof id !== 'string') throw new TypeError('getFile expects a string ID');
  const element = document.getElementById(id);
  if (!(element instanceof HTMLInputElement)) throw new TypeError('Element is not an input');
  return element.files.length > 0 ? element.files[0] : null;
};
