/* D&D Companion - Modal-Hilfsfunktionen */

const DndModal = (() => {
  'use strict';

  let currentModal = null;
  let overlayEl = null;
  let modalEl = null;

  /**
   * Initialisiert das Modal-System
   */
  function init() {
    overlayEl = DndUtils.createElement('div', 'modal-overlay');
    overlayEl.setAttribute('role', 'dialog');
    overlayEl.setAttribute('aria-modal', 'true');
    document.body.appendChild(overlayEl);

    // Schließe Modal bei Klick auf Overlay
    overlayEl.addEventListener('click', (e) => {
      if (e.target === overlayEl) {
        close();
      }
    });

    // Schließe Modal bei ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && currentModal) {
        close();
      }
    });
  }

  /**
   * Öffnet ein Modal mit HTML
   */
  function open(title, content, buttons = []) {
    if (!overlayEl) init();

    // Alte Modal entfernen
    if (modalEl) modalEl.remove();

    // Neue Modal erstellen
    modalEl = DndUtils.createElement('div', 'modal');

    const header = DndUtils.createElement('div', 'modal-header');
    const titleEl = DndUtils.createElement('h2', 'modal-title');
    titleEl.textContent = title;

    const closeBtn = DndUtils.createElement('button', 'modal-close');
    closeBtn.textContent = '✕';
    closeBtn.setAttribute('aria-label', 'Schließen');
    closeBtn.addEventListener('click', close);

    header.appendChild(titleEl);
    header.appendChild(closeBtn);

    const bodyEl = DndUtils.createElement('div', 'modal-body');
    bodyEl.innerHTML = content;

    const footerEl = DndUtils.createElement('div', 'modal-footer');

    buttons.forEach(btn => {
      const btnEl = DndUtils.createElement('button', `modal-btn ${btn.className || ''}`);
      btnEl.textContent = btn.text;
      btnEl.addEventListener('click', () => {
        btn.onClick?.();
        if (btn.closeOnClick !== false) {
          close();
        }
      });
      footerEl.appendChild(btnEl);
    });

    modalEl.appendChild(header);
    modalEl.appendChild(bodyEl);
    if (buttons.length > 0) {
      modalEl.appendChild(footerEl);
    }

    overlayEl.appendChild(modalEl);
    overlayEl.classList.add('active');

    currentModal = modalEl;
    document.body.style.overflow = 'hidden';

    // Focus in Modal
    const focusable = modalEl.querySelector('button, input, select, textarea, [tabindex]');
    if (focusable) focusable.focus();

    return modalEl;
  }

  /**
   * Schließt das aktuelle Modal
   */
  function close() {
    if (overlayEl) {
      overlayEl.classList.remove('active');
      document.body.style.overflow = '';
      currentModal = null;
    }
  }

  /**
   * Input-Dialog
   */
  function inputDialog(title, label, defaultValue = '', type = 'text') {
    return new Promise((resolve) => {
      const inputId = 'modal-input-' + DndUtils.generateId();

      const content = `
        <div class="input-group">
          <label for="${inputId}" class="input-label">${DndUtils.escapeHtml(label)}</label>
          <input type="${type}" id="${inputId}" class="modal-input" value="${DndUtils.escapeHtml(defaultValue)}" />
        </div>
      `;

      const buttons = [
        {
          text: 'Abbrechen',
          className: '',
          onClick: () => resolve(null)
        },
        {
          text: 'OK',
          className: 'primary',
          onClick: () => {
            const inputEl = document.getElementById(inputId);
            resolve(inputEl.value);
          }
        }
      ];

      open(title, content, buttons);

      const inputEl = document.getElementById(inputId);
      inputEl.focus();
      inputEl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          resolve(inputEl.value);
          close();
        }
      });
    });
  }

  /**
   * Bestätigungsdialog
   */
  function confirmDialog(title, message, details = '') {
    return new Promise((resolve) => {
      let content = `<p class="confirmation-message">${DndUtils.escapeHtml(message)}</p>`;

      if (details) {
        content += `<div class="confirmation-details">${DndUtils.escapeHtml(details)}</div>`;
      }

      const buttons = [
        {
          text: 'Abbrechen',
          className: '',
          onClick: () => resolve(false)
        },
        {
          text: 'Ja, fortfahren',
          className: 'danger',
          onClick: () => resolve(true)
        }
      ];

      open(title, content, buttons);
    });
  }

  /**
   * Warnung anzeigen
   */
  function warningDialog(title, message) {
    const content = `<div class="confirmation-warning">${DndUtils.escapeHtml(message)}</div>`;

    const buttons = [
      {
        text: 'OK',
        className: 'primary',
        onClick: () => {}
      }
    ];

    open(title, content, buttons);
  }

  /**
   * Erfolgs-Dialog
   */
  function successDialog(title, message) {
    const content = `<div class="success-message">${DndUtils.escapeHtml(message)}</div>`;

    const buttons = [
      {
        text: 'OK',
        className: 'primary',
        onClick: () => {}
      }
    ];

    open(title, content, buttons);
  }

  /**
   * Fehler-Dialog
   */
  function errorDialog(title, errors = []) {
    let content = `<div class="error-message"><strong>Fehler:</strong>`;

    if (Array.isArray(errors)) {
      content += '<ul>';
      errors.forEach(error => {
        content += `<li>${DndUtils.escapeHtml(error)}</li>`;
      });
      content += '</ul>';
    } else {
      content += `<p>${DndUtils.escapeHtml(String(errors))}</p>`;
    }

    content += '</div>';

    const buttons = [
      {
        text: 'OK',
        className: 'primary',
        onClick: () => {}
      }
    ];

    open(title, content, buttons);
  }

  /**
   * Radio-Button-Dialog
   */
  function radioDialog(title, options, selected = null) {
    return new Promise((resolve) => {
      let content = '<div class="radio-group">';

      options.forEach((option, index) => {
        const radioId = 'radio-' + DndUtils.generateId();
        content += `
          <div class="radio-item">
            <input type="radio" id="${radioId}" name="radio-group" value="${option.value}" ${selected === option.value ? 'checked' : ''} />
            <label for="${radioId}">${DndUtils.escapeHtml(option.label)}</label>
          </div>
        `;
      });

      content += '</div>';

      const buttons = [
        {
          text: 'Abbrechen',
          className: '',
          onClick: () => resolve(null)
        },
        {
          text: 'OK',
          className: 'primary',
          onClick: () => {
            const selected = document.querySelector('input[name="radio-group"]:checked');
            resolve(selected ? selected.value : null);
          }
        }
      ];

      open(title, content, buttons);
    });
  }

  return {
    init,
    open,
    close,
    inputDialog,
    confirmDialog,
    warningDialog,
    successDialog,
    errorDialog,
    radioDialog,
    get currentModal() {
      return currentModal;
    }
  };
})();
