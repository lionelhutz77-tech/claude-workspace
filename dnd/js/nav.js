/* D&D Companion - Navigation */

const DndNav = (() => {
  'use strict';

  const views = {
    dashboard: { label: '📊 Dashboard', order: 1 },
    combat: { label: '⚔ Kampf', order: 2 },
    spells: { label: '✨ Zauber', order: 3 },
    inventory: { label: '🎒 Inventar', order: 4 },
    notes: { label: '📝 Notizen', order: 5 },
    settings: { label: '⚙ Einstellungen', order: 6 }
  };

  let currentView = 'dashboard';

  /**
   * Setzt die aktuelle Ansicht
   */
  function setCurrentView(view) {
    if (views[view]) {
      currentView = view;
      updateNavBar();
      return true;
    }
    return false;
  }

  /**
   * Gibt die aktuelle Ansicht zurück
   */
  function getCurrentView() {
    return currentView;
  }

  /**
   * Aktualisiert die Navbar-Hervorhebung
   */
  function updateNavBar() {
    const navButtons = document.querySelectorAll('.nav-button');
    navButtons.forEach(btn => {
      if (btn.dataset.view === currentView) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  /**
   * Gibt alle verfügbaren Ansichten zurück
   */
  function getAvailableViews() {
    return Object.entries(views)
      .sort((a, b) => a[1].order - b[1].order)
      .map(([key, value]) => ({ key, ...value }));
  }

  /**
   * Navigation zur Dashboard
   */
  function toDashboard(character) {
    setCurrentView('dashboard');
    DndUI.renderDashboard(character);
  }

  /**
   * Navigation zu Kampf
   */
  function toCombat(character) {
    setCurrentView('combat');
    DndUI.switchView('combat', character);
  }

  /**
   * Navigation zu Inventar
   */
  function toInventory(character) {
    setCurrentView('inventory');
    DndUI.switchView('inventory', character);
  }

  /**
   * Navigation zu Notizen
   */
  function toNotes(character) {
    setCurrentView('notes');
    DndUI.switchView('notes', character);
  }

  /**
   * Navigation zu Einstellungen
   */
  function toSettings(character) {
    setCurrentView('settings');
    DndUI.switchView('settings', character);
  }

  /**
   * Navigation zu Verlauf
   */
  function toHistory(character) {
    setCurrentView('history');
    DndUI.switchView('history', character);
  }

  return {
    setCurrentView,
    getCurrentView,
    updateNavBar,
    getAvailableViews,
    toDashboard,
    toCombat,
    toInventory,
    toNotes,
    toSettings,
    toHistory
  };
})();
