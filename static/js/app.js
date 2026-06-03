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

// Interatividade das questões online geradas fora do simulado.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-question-card]').forEach((card) => {
    card.querySelectorAll('[data-option]').forEach((button) => {
      button.addEventListener('click', () => {
        const correct = (button.dataset.correct || '').trim().toUpperCase().slice(0, 1);
        const chosen = (button.dataset.letter || '').trim().toUpperCase().slice(0, 1);
        card.querySelectorAll('[data-option]').forEach((opt) => {
          const letter = (opt.dataset.letter || '').trim().toUpperCase().slice(0, 1);
          opt.classList.remove('option-correct', 'option-wrong');
          if (correct && letter === correct) opt.classList.add('option-correct');
        });
        if (correct && chosen !== correct) button.classList.add('option-wrong');
        const details = card.querySelector('.commented-answer');
        if (details) details.open = true;
      });
    });
  });

  const course = document.querySelector('[data-course-select]');
  const goal = document.querySelector('[data-objective-select]');
  const objectiveMap = {
    direito: ['OAB', 'Concursos públicos', 'Provas da faculdade', 'Carreira acadêmica', 'Residência jurídica', 'Outros'],
    medicina: ['Provas da faculdade', 'Residência médica', 'Internato', 'Revisão clínica', 'Outros'],
    enfermagem: ['Provas da faculdade', 'Concursos', 'Residência multiprofissional', 'Prática clínica', 'Outros'],
    psicologia: ['Provas da faculdade', 'Concursos', 'Clínica', 'Pesquisa acadêmica', 'Outros'],
    administracao: ['Provas da faculdade', 'Concursos', 'Certificações', 'Mercado de trabalho', 'Outros'],
    engenharia: ['Provas da faculdade', 'Concursos', 'Projetos', 'Certificações', 'Outros'],
    pedagogia: ['Provas da faculdade', 'Concursos', 'Prática docente', 'Pesquisa acadêmica', 'Outros'],
    contabilidade: ['Provas da faculdade', 'CRC', 'Concursos', 'Mercado de trabalho', 'Outros'],
    geral: ['Provas', 'Concursos', 'Revisão geral', 'Aprendizado contínuo', 'Outros'],
    outros: ['Objetivo personalizado']
  };
  if (course && goal) {
    course.addEventListener('change', () => {
      const current = goal.value;
      goal.innerHTML = '<option value="">Selecione um objetivo</option>';
      (objectiveMap[course.value] || objectiveMap.geral).forEach((item) => {
        const option = document.createElement('option');
        option.value = item;
        option.textContent = item;
        if (item === current) option.selected = true;
        goal.appendChild(option);
      });
    });
  }
});
