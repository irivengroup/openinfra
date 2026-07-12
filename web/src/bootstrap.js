const root = document.getElementById('openinfra-root');

import('./main.jsx').catch((error) => {
  console.error('OpenInfra React startup failed', error);
  if (!root) return;
  const main = document.createElement('main');
  main.setAttribute('role', 'main');
  main.className = 'container py-5';
  const alert = document.createElement('div');
  alert.className = 'alert alert-danger';
  alert.setAttribute('role', 'alert');
  alert.textContent = 'OpenInfra Web cannot start.';
  main.append(alert);
  root.replaceChildren(main);
});
