document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('appSidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const appShell = document.querySelector('.app-shell');
  const sidebarToggle = document.querySelector('.sidebar-toggle');
  
  // Handle desktop sidebar collapse state
  const SIDEBAR_COLLAPSE_KEY = 'inventory_app_sidebar_collapsed';
  const DESKTOP_BREAKPOINT = 992;

  function isDesktop() {
    return window.innerWidth > DESKTOP_BREAKPOINT;
  }

  function updateSidebarToggleState() {
    if (!sidebarToggle) return;

    if (isDesktop()) {
      sidebarToggle.setAttribute('aria-expanded', String(!appShell?.classList.contains('sidebar-collapsed')));
    } else {
      sidebarToggle.setAttribute('aria-expanded', String(sidebar?.classList.contains('show')));
    }
  }

  function notifyLayoutChanged() {
    window.dispatchEvent(new Event('resize'));
  }
  
  // Restore sidebar collapse state from localStorage
  const isSidebarCollapsed = localStorage.getItem(SIDEBAR_COLLAPSE_KEY) === 'true';
  if (isSidebarCollapsed && appShell && isDesktop()) {
    appShell.classList.add('sidebar-collapsed');
  }
  updateSidebarToggleState();
  
  // Desktop sidebar toggle (non-mobile)
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', (event) => {
      event.preventDefault();

      if (isDesktop()) {
        // Desktop: toggle collapse state
        if (appShell) {
          appShell.classList.toggle('sidebar-collapsed');
          const isNowCollapsed = appShell.classList.contains('sidebar-collapsed');
          localStorage.setItem(SIDEBAR_COLLAPSE_KEY, isNowCollapsed);
          updateSidebarToggleState();
          window.setTimeout(notifyLayoutChanged, 320);
        }
      } else {
        // Mobile: toggle sidebar visibility
        if (sidebar) {
          sidebar.classList.toggle('show');
          if (backdrop) {
            backdrop.classList.toggle('d-none');
          }
          updateSidebarToggleState();
        }
      }
    });
  }

  // Mobile sidebar backdrop handling
  if (sidebar && backdrop) {
    backdrop.addEventListener('click', () => {
      sidebar.classList.remove('show');
      backdrop.classList.add('d-none');
      updateSidebarToggleState();
    });
  }
  
  // Handle window resize - reset state on breakpoint change
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      if (!isDesktop() && appShell) {
        // On mobile, ensure we're not in collapsed mode
        appShell.classList.remove('sidebar-collapsed');
        sidebar?.classList.remove('show');
        backdrop?.classList.add('d-none');
      } else if (isDesktop() && appShell && localStorage.getItem(SIDEBAR_COLLAPSE_KEY) === 'true') {
        appShell.classList.add('sidebar-collapsed');
      }
      updateSidebarToggleState();
      notifyLayoutChanged();
    }, 250);
  });
  
  // Close sidebar when a link is clicked on mobile
  if (sidebar) {
    const sidebarLinks = sidebar.querySelectorAll('a.nav-link');
    sidebarLinks.forEach(link => {
      link.addEventListener('click', () => {
        if (!isDesktop()) {
          sidebar.classList.remove('show');
          if (backdrop) {
            backdrop.classList.add('d-none');
          }
          updateSidebarToggleState();
        }
      });
    });
  }
});
