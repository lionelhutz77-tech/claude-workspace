/* D&D Companion - Hauptanwendung */

const DndApp = (() => {
  'use strict';

  let currentCharacter = null;

  /**
   * Initialisiert die Anwendung
   */
  async function init() {
    // Prüfe localStorage-Verfügbarkeit
    if (!DndStorage.isAvailable()) {
      alert('Fehler: localStorage nicht verfügbar. Die App benötigt localStorage zum Speichern von Daten.');
      return;
    }

    // Initialisiere Module
    DndModal.init();

    // Lade oder erstelle Charakter
    let character = DndStorage.loadCharacter();

    if (!character) {
      character = DndCharacter.create('Charakter ohne Namen');
      DndStorage.saveCharacter(character);
    }

    // Validiere Charakter
    const validation = DndCharacter.validate(character);
    if (!validation.valid) {
      console.warn('Charaktervalidierungswarnungen:', validation.errors);
    }

    // Initialisiere Transaktionssystem
    DndTransaction.init(character);
    currentCharacter = character;

    // Rendere Dashboard
    DndUI.renderDashboard(character);

    // Service Worker registrieren
    if ('serviceWorker' in navigator) {
      try {
        await navigator.serviceWorker.register('service-worker.js', { scope: '/schulweg-nrw/dnd/' });
        console.log('Service Worker registriert');
      } catch (e) {
        console.warn('Service Worker Registrierung fehlgeschlagen:', e);
      }
    }

    // Auto-Save nach jeder Änderung
    setupAutoSave();

    console.log('D&D Companion initialisiert');
  }

  /**
   * Auto-Save einrichten
   */
  function setupAutoSave() {
    setInterval(() => {
      if (currentCharacter) {
        DndStorage.saveCharacter(currentCharacter);
        console.log('Auto-save durchgeführt');
      }
    }, 30000); // Alle 30 Sekunden
  }

  /**
   * Speichert den aktuellen Charakter
   */
  function saveCharacter() {
    if (currentCharacter) {
      DndStorage.saveCharacter(currentCharacter);
      return true;
    }
    return false;
  }

  /**
   * Gibt den aktuellen Charakter zurück
   */
  function getCharacter() {
    return currentCharacter;
  }

  /**
   * Setzt einen neuen Charakter
   */
  function setCharacter(character) {
    currentCharacter = character;
    DndTransaction.init(character);
    DndStorage.saveCharacter(character);
    DndUI.renderDashboard(character);
  }

  /**
   * Exportiert den Charakter
   */
  async function exportCharacter() {
    try {
      const history = DndTransaction.getHistory();
      const favorites = DndStorage.loadFavorites();

      const exportData = DndStorage.exportCharacter(currentCharacter, history, favorites);

      const dataStr = JSON.stringify(exportData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);

      const link = document.createElement('a');
      link.href = url;
      link.download = `dnd_character_${currentCharacter.meta.name}_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      DndUtils.showNotification('Charakter exportiert!');
      return true;
    } catch (e) {
      console.error('Export-Fehler:', e);
      DndUtils.showNotification('Export-Fehler: ' + e.message, 'error');
      return false;
    }
  }

  /**
   * Importiert einen Charakter
   */
  async function importCharacter() {
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json';

      input.onchange = async (e) => {
        try {
          const file = e.target.files[0];
          if (!file) {
            resolve(false);
            return;
          }

          const fileContent = await file.text();
          const importData = JSON.parse(fileContent);

          const validation = DndStorage.validateImportData(importData);
          if (!validation.valid) {
            DndModal.errorDialog('Import-Fehler', validation.errors);
            resolve(false);
            return;
          }

          const confirmed = await DndModal.confirmDialog(
            'Charakter importieren?',
            `Name: ${importData.character.meta.name}`,
            `Aktueller Charakter wird überschrieben.`
          );

          if (confirmed) {
            // Backup erstellen
            DndStorage.createBackup(currentCharacter);

            // Charakter importieren
            setCharacter(importData.character);

            // History optional importieren
            if (importData.history) {
              DndStorage.saveHistory(importData.history);
            }

            DndUtils.showNotification('Charakter importiert!');
            resolve(true);
          } else {
            resolve(false);
          }
        } catch (e) {
          console.error('Import-Fehler:', e);
          DndModal.errorDialog('Import-Fehler', [e.message]);
          resolve(false);
        }
      };

      input.click();
    });
  }

  /**
   * Gibt Statistiken aus
   */
  function getStats() {
    return {
      character: currentCharacter ? currentCharacter.meta.name : 'Keine',
      storageInfo: DndStorage.getStorageInfo(),
      historyStats: DndTransaction.getHistoryStats()
    };
  }

  /**
   * Startet die Anwendung beim Laden
   */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    init,
    saveCharacter,
    getCharacter,
    setCharacter,
    exportCharacter,
    importCharacter,
    getStats
  };
})();

// Global-Zugriff für Debugging
window.DndApp = DndApp;
window.DndUtils = DndUtils;
window.DndStorage = DndStorage;
window.DndTransaction = DndTransaction;
window.DndCharacter = DndCharacter;
window.DndResources = DndResources;
window.DndUI = DndUI;
