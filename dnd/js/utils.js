/* D&D Companion - Utility-Funktionen */

const DndUtils = (() => {
  'use strict';

  /**
   * Generiert eine UUID v4
   */
  function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  /**
   * Aktuelle ISO-Zeitstempel
   */
  function getCurrentTimestamp() {
    return new Date().toISOString();
  }

  /**
   * Formatiert ein Datum auf Deutsch
   */
  function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('de-DE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  }

  /**
   * Formatiert eine Uhrzeit auf Deutsch
   */
  function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('de-DE', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  /**
   * Formatiert DateTime
   */
  function formatDateTime(isoString) {
    return formatDate(isoString) + ' ' + formatTime(isoString);
  }

  /**
   * Validiert eine Zahl im Bereich
   */
  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  /**
   * Deep Clone von Objekten
   */
  function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => deepClone(item));
    if (obj instanceof Object) {
      const cloned = {};
      for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
          cloned[key] = deepClone(obj[key]);
        }
      }
      return cloned;
    }
  }

  /**
   * Merged zwei Objekte
   */
  function merge(target, source) {
    const result = deepClone(target);
    for (const key in source) {
      if (source.hasOwnProperty(key)) {
        if (typeof source[key] === 'object' && source[key] !== null && !Array.isArray(source[key])) {
          result[key] = merge(result[key] || {}, source[key]);
        } else {
          result[key] = deepClone(source[key]);
        }
      }
    }
    return result;
  }

  /**
   * DOM-Element erstellen
   */
  function createElement(tag, className = '', innerHTML = '') {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (innerHTML) el.innerHTML = innerHTML;
    return el;
  }

  /**
   * Zeigt/versteckt ein Element
   */
  function show(el) {
    if (el) el.classList.remove('hidden');
  }

  function hide(el) {
    if (el) el.classList.add('hidden');
  }

  /**
   * Event-Delegation
   */
  function on(el, eventType, selector, handler) {
    if (!el) return;
    el.addEventListener(eventType, (e) => {
      const target = e.target.closest(selector);
      if (target) handler.call(target, e);
    });
  }

  /**
   * HTML-Entity Encoding (XSS-Protection)
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Debounce-Funktion
   */
  function debounce(fn, delay) {
    let timeoutId;
    return function(...args) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  /**
   * Speichert einen Wert in der Session (für Undo-Stacks, etc.)
   */
  const sessionData = {};

  function setSession(key, value) {
    sessionData[key] = value;
  }

  function getSession(key) {
    return sessionData[key];
  }

  function clearSession() {
    for (const key in sessionData) {
      delete sessionData[key];
    }
  }

  /**
   * Validiert HP-Werte
   */
  function validateHpValues(current, maximum, temporary = 0) {
    return {
      current: clamp(current, 0, maximum),
      maximum: Math.max(1, maximum),
      temporary: Math.max(0, temporary)
    };
  }

  /**
   * Berechnet Schaden mit Temp-HP-Logik
   */
  function calculateDamage(damage, currentHp, maxHp, tempHp) {
    const tempDamage = Math.min(tempHp, damage);
    const remainingDamage = damage - tempDamage;
    const newHp = Math.max(0, currentHp - remainingDamage);
    const newTempHp = Math.max(0, tempHp - tempDamage);

    return {
      damageToTemp: tempDamage,
      damageToHp: remainingDamage,
      newHp,
      newTempHp,
      totalDamage: damage
    };
  }

  /**
   * Berechnet Heilung
   */
  function calculateHealing(healing, currentHp, maxHp) {
    const actualHealing = Math.min(healing, maxHp - currentHp);
    const newHp = currentHp + actualHealing;
    const overkill = Math.max(0, healing - actualHealing);

    return {
      healing: actualHealing,
      newHp: clamp(newHp, 0, maxHp),
      overkill
    };
  }

  /**
   * Bestimmt HP-Zustand als String
   */
  function getHpStatus(current, maximum) {
    const ratio = current / maximum;
    if (ratio > 0.5) return 'full';
    if (ratio > 0.25) return 'good';
    if (ratio > 0) return 'low';
    return 'critical';
  }

  /**
   * Bestimmt HTML-Klasse für HP-Farbe
   */
  function getHpClass(current, maximum) {
    const status = getHpStatus(current, maximum);
    return `hp-bar-fill ${status}`;
  }

  /**
   * Zeigt eine Benachrichtigung an
   */
  function showNotification(message, type = 'info', duration = 3000) {
    const notification = createElement('div', `notification notification-${type}`);
    notification.textContent = message;
    notification.setAttribute('role', 'status');
    notification.setAttribute('aria-live', 'polite');

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, duration);
  }

  /**
   * Validiert Charakterdaten
   */
  function validateCharacterData(data) {
    const errors = [];

    if (!data.meta || !data.meta.id) errors.push('Charakter-ID fehlt');
    if (!data.meta.name) errors.push('Charaktername fehlt');
    if (!data.basics || !data.basics.class) errors.push('Klasse fehlt');
    if (!data.hitpoints || typeof data.hitpoints.max !== 'number') errors.push('Maximale HP ungültig');
    if (data.hitpoints.max < 1) errors.push('Maximale HP müssen mindestens 1 sein');

    return {
      valid: errors.length === 0,
      errors
    };
  }

  return {
    generateId,
    getCurrentTimestamp,
    formatDate,
    formatTime,
    formatDateTime,
    clamp,
    deepClone,
    merge,
    createElement,
    show,
    hide,
    on,
    escapeHtml,
    debounce,
    setSession,
    getSession,
    clearSession,
    validateHpValues,
    calculateDamage,
    calculateHealing,
    getHpStatus,
    getHpClass,
    showNotification,
    validateCharacterData
  };
})();
