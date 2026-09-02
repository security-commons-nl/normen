// Tab navigation with hash deep links, plus copy buttons for the KQL blocks.
// Without JavaScript the page degrades to all sections stacked vertically.
(function () {
  'use strict';

  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tab'));
  var panels = Array.prototype.slice.call(document.querySelectorAll('.tab-panel'));
  if (tabs.length === 0 || panels.length === 0) return;

  document.body.classList.add('tabbed');

  function activate(id, updateHash) {
    var known = panels.some(function (p) { return p.id === id; });
    if (!known) id = panels[0].id;
    panels.forEach(function (p) { p.classList.toggle('actief', p.id === id); });
    tabs.forEach(function (t) {
      t.setAttribute('aria-selected', t.dataset.target === id ? 'true' : 'false');
    });
    if (updateHash && '#' + id !== window.location.hash) {
      history.replaceState(null, '', '#' + id);
    }
    window.scrollTo(0, 0);
  }

  tabs.forEach(function (t) {
    t.addEventListener('click', function () { activate(t.dataset.target, true); });
  });

  // In-content links to other tabs (rewritten from .md links) and the hash on load.
  window.addEventListener('hashchange', function () {
    activate(window.location.hash.slice(1), false);
  });
  activate(window.location.hash.slice(1), false);

  // Open all query details when printing.
  window.addEventListener('beforeprint', function () {
    Array.prototype.forEach.call(document.querySelectorAll('details'), function (d) {
      d.setAttribute('open', '');
    });
  });

  // Copy buttons for query blocks.
  Array.prototype.forEach.call(document.querySelectorAll('[data-copy]'), function (btn) {
    btn.addEventListener('click', function () {
      var code = btn.parentElement.querySelector('code');
      navigator.clipboard.writeText(code.textContent).then(function () {
        var oud = btn.textContent;
        btn.textContent = 'Gekopieerd';
        setTimeout(function () { btn.textContent = oud; }, 1500);
      });
    });
  });
})();
