/* D&D Companion - localStorage-Wrapper mit dnd_* Namespace */

const DndStorage = (() => {
  'use strict';

  const PREFIX = 'dnd_';
  const KEYS = {
    CHARACTER: PREFIX + 'character',
    HISTORY: PREFIX + 'history',
    FAVORITES: PREFIX + 'favorites',
    SETTINGS: PREFIX + 'settings',
    BACKUPS: PREFIX + 'backups'
  };

  /**
   * Speichert ein Objekt
   */
  function setItem(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      console.error('localStorage Fehler beim Speichern:', e);
      return false;
    }
  }

  /**
   * Lädt ein Objekt
   */
  function getItem(key, defaultValue = null) {
    try {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : defaultValue;
    } catch (e) {
      console.error('localStorage Fehler beim Laden:', e);
      return defaultValue;
    }
  }

  /**
   * Entfernt einen Eintrag
   */
  function removeItem(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (e) {
      console.error('localStorage Fehler beim Löschen:', e);
      return false;
    }
  }

  /**
   * Speichert den aktuellen Charakter
   */
  function saveCharacter(character) {
    return setItem(KEYS.CHARACTER, character);
  }

  /**
   * Lädt den aktuellen Charakter
   */
  function loadCharacter() {
    return getItem(KEYS.CHARACTER);
  }

  /**
   * Speichert den Änderungsverlauf
   */
  function saveHistory(history) {
    return setItem(KEYS.HISTORY, history);
  }

  /**
   * Lädt den Änderungsverlauf
   */
  function loadHistory() {
    return getItem(KEYS.HISTORY, []);
  }

  /**
   * Speichert Favoriten
   */
  function saveFavorites(favorites) {
    return setItem(KEYS.FAVORITES, favorites);
  }

  /**
   * Lädt Favoriten
   */
  function loadFavorites() {
    return getItem(KEYS.FAVORITES, []);
  }

  /**
   * Speichert Einstellungen
   */
  function saveSettings(settings) {
    return setItem(KEYS.SETTINGS, settings);
  }

  /**
   * Lädt Einstellungen
   */
  function loadSettings() {
    return getItem(KEYS.SETTINGS, {
      theme: 'dark',
      soundEnabled: true,
      notificationsEnabled: true
    });
  }

  /**
   * Erstellt ein lokales Backup
   */
  function createBackup(character) {
    const backups = getItem(KEYS.BACKUPS, []);
    const backup = {
      id: DndUtils.generateId(),
      characterId: character.meta.id,
      characterName: character.meta.name,
      timestamp: DndUtils.getCurrentTimestamp(),
      data: DndUtils.deepClone(character)
    };

    backups.push(backup);

    // Behalte maximal 10 Backups
    if (backups.length > 10) {
      backups.shift();
    }

    setItem(KEYS.BACKUPS, backups);
    return backup;
  }

  /**
   * Lädt ein Backup
   */
  function loadBackup(backupId) {
    const backups = getItem(KEYS.BACKUPS, []);
    const backup = backups.find(b => b.id === backupId);
    return backup ? backup.data : null;
  }

  /**
   * Listet alle Backups
   */
  function listBackups() {
    return getItem(KEYS.BACKUPS, []);
  }

  /**
   * Exportiert den kompletten Charakter
   */
  function exportCharacter(character, history = null, favorites = null, includeVersion = true) {
    const exportData = {
      appVersion: '1.0.0',
      schemaVersion: 1,
      characterVersion: 1,
      ruleset: 'dnd5e',
      exportDate: DndUtils.getCurrentTimestamp(),
      character: DndUtils.deepClone(character)
    };

    if (history) {
      exportData.history = DndUtils.deepClone(history);
    }

    if (favorites) {
      exportData.favorites = DndUtils.deepClone(favorites);
    }

    return exportData;
  }

  /**
   * Importiert einen Charakter
   */
  function importCharacter(importData) {
    const validation = validateImportData(importData);

    if (!validation.valid) {
      return {
        success: false,
        errors: validation.errors
      };
    }

    return {
      success: true,
      character: importData.character,
      history: importData.history || [],
      favorites: importData.favorites || []
    };
  }

  /**
   * Validiert Importdaten
   */
  function validateImportData(data) {
    const errors = [];

    if (!data || typeof data !== 'object') {
      errors.push('Ungültiges Dateiformat');
      return { valid: false, errors };
    }

    if (!data.character) {
      errors.push('Charakter-Daten fehlen');
    }

    if (data.schemaVersion && data.schemaVersion > 1) {
      errors.push('Schema-Version nicht unterstützt');
    }

    if (data.character) {
      const charValidation = DndUtils.validateCharacterData(data.character);
      if (!charValidation.valid) {
        errors.push(...charValidation.errors);
      }
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * Löscht alles (Vorsicht!)
   */
  function clearAllData() {
    for (const key in KEYS) {
      removeItem(KEYS[key]);
    }
  }

  /**
   * Prüft localStorage-Größe
   */
  function getStorageInfo() {
    let totalSize = 0;
    for (const key in KEYS) {
      const value = localStorage.getItem(KEYS[key]);
      if (value) {
        totalSize += value.length;
      }
    }

    return {
      totalBytes: totalSize,
      totalKb: (totalSize / 1024).toFixed(2),
      itemCount: Object.keys(KEYS).filter(k => localStorage.getItem(KEYS[k])).length
    };
  }

  /**
   * Prüft, ob localStorage verfügbar ist
   */
  function isAvailable() {
    try {
      const test = '__test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (e) {
      return false;
    }
  }

  return {
    KEYS,
    setItem,
    getItem,
    removeItem,
    saveCharacter,
    loadCharacter,
    saveHistory,
    loadHistory,
    saveFavorites,
    loadFavorites,
    saveSettings,
    loadSettings,
    createBackup,
    loadBackup,
    listBackups,
    exportCharacter,
    importCharacter,
    validateImportData,
    clearAllData,
    getStorageInfo,
    isAvailable
  };
})();
