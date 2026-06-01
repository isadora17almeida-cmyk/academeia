document.addEventListener('DOMContentLoaded', () => {
  const menuButton = document.querySelector('[data-menu-toggle]');
  const menu = document.querySelector('[data-menu]');
  if (menuButton && menu) {
    menuButton.addEventListener('click', () => menu.classList.toggle('open'));
  }

  const appShell = document.querySelector('[data-app-shell]');
  const sidebar = document.querySelector('[data-sidebar]');
  const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
  const sidebarBackdrop = document.querySelector('[data-sidebar-backdrop]');

  const isMobileSidebar = () => window.matchMedia('(max-width: 1100px)').matches;
  const closeMobileSidebar = () => document.body.classList.remove('sidebar-open');

  if (appShell && sidebarToggle) {
    const stored = localStorage.getItem('academeia_sidebar_collapsed');
    if (stored === '1') appShell.classList.add('sidebar-collapsed');

    sidebarToggle.addEventListener('click', () => {
      if (isMobileSidebar()) {
        document.body.classList.toggle('sidebar-open');
      } else {
        appShell.classList.toggle('sidebar-collapsed');
        localStorage.setItem('academeia_sidebar_collapsed', appShell.classList.contains('sidebar-collapsed') ? '1' : '0');
      }
    });
  }

  if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeMobileSidebar);
  if (sidebar) {
    sidebar.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMobileSidebar));
  }

  const reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) entry.target.classList.add('visible');
      });
    }, { threshold: 0.12 });
    reveals.forEach((el) => observer.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add('visible'));
  }

  document.querySelectorAll('[data-loading-form]').forEach((form) => {
    form.addEventListener('submit', () => {
      const spinner = form.querySelector('.spinner');
      const progress = form.querySelector('[data-progress]');
      if (spinner) spinner.classList.remove('hidden');
      if (progress) progress.classList.remove('hidden');
    });
  });

  document.querySelectorAll('[data-upload-box]').forEach((box) => {
    ['dragenter', 'dragover'].forEach((eventName) => {
      box.addEventListener(eventName, (event) => {
        event.preventDefault();
        box.classList.add('dragover');
      });
    });
    ['dragleave', 'drop'].forEach((eventName) => {
      box.addEventListener(eventName, (event) => {
        event.preventDefault();
        box.classList.remove('dragover');
      });
    });
  });

  document.querySelectorAll('[data-flip-card]').forEach((card) => {
    card.addEventListener('click', (event) => {
      if (event.target.closest('form') || event.target.closest('button')) return;
      card.classList.toggle('flipped');
    });
  });
});
