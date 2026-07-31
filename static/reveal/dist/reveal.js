/*
 * Schlanke lokale reveal.js-kompatible Laufzeit fuer diese Signage-Anwendung.
 * Unterstuetzt die verwendeten APIs: initialize, next, on, getCurrentSlide und configure.
 */
(function () {
  'use strict';

  var state = { slides: [], index: 0, config: {}, listeners: {}, timer: null, initialized: false };

  function emit(name, detail) {
    (state.listeners[name] || []).forEach(function (listener) { listener(detail); });
  }

  function currentDelay() {
    var slide = state.slides[state.index];
    if (!slide) return 0;
    var configured = slide.getAttribute('data-autoslide');
    return configured === null ? Number(state.config.autoSlide || 0) : Number(configured);
  }

  function schedule() {
    window.clearTimeout(state.timer);
    var delay = currentDelay();
    if (delay > 0) state.timer = window.setTimeout(api.next, delay);
  }

  function show(index) {
    if (!state.slides.length) return;
    var lastIndex = state.slides.length - 1;
    if (index > lastIndex) index = state.config.loop ? 0 : lastIndex;
    if (index < 0) index = state.config.loop ? lastIndex : 0;

    state.slides.forEach(function (slide, slideIndex) {
      slide.classList.toggle('present', slideIndex === index);
      slide.setAttribute('aria-hidden', slideIndex === index ? 'false' : 'true');
    });
    state.index = index;
    schedule();
    emit('slidechanged', { currentSlide: state.slides[index], indexh: index });
  }

  var api = {
    initialize: function (options) {
      state.config = Object.assign({ autoSlide: 0, loop: false }, options || {});
      var deck = document.querySelector('.reveal .slides');
      state.slides = deck ? Array.prototype.slice.call(deck.children).filter(function (node) {
        return node.tagName === 'SECTION';
      }) : [];
      state.initialized = true;
      show(0);
      emit('ready', { currentSlide: state.slides[0], indexh: 0 });
      document.addEventListener('keydown', function (event) {
        if (event.key === 'ArrowRight' || event.key === ' ') api.next();
        if (event.key === 'ArrowLeft') api.prev();
      });
      return api;
    },
    next: function () { show(state.index + 1); },
    prev: function () { show(state.index - 1); },
    getCurrentSlide: function () { return state.slides[state.index] || null; },
    configure: function (options) { state.config = Object.assign(state.config, options || {}); schedule(); },
    on: function (name, listener) {
      state.listeners[name] = state.listeners[name] || [];
      state.listeners[name].push(listener);
      if (name === 'ready' && state.initialized) listener({ currentSlide: api.getCurrentSlide(), indexh: state.index });
    }
  };

  window.Reveal = api;
}());
