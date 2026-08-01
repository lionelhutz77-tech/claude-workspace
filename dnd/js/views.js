/* D&D Companion - Views (Placeholder für erweiterte Ansichten) */

const DndViews = (() => {
  'use strict';

  /**
   * Rendert eine Nachricht über fehlende Features
   */
  function renderPlaceholder(title, feature) {
    const html = `
      <div style="padding: 20px; max-width: 800px; margin: 0 auto;">
        <div style="margin-bottom: 20px;">
          <button onclick="DndNav.toDashboard()" style="padding: 8px 16px; margin-right: 8px;">← Zurück</button>
          <button onclick="DndNav.toDashboard()" style="padding: 8px 16px;">📊 Dashboard</button>
        </div>
        <h2>${DndUtils.escapeHtml(title)}</h2>
        <p style="color: var(--text-secondary); margin-top: 20px;">
          ${DndUtils.escapeHtml(feature)} wird in einer zukünftigen Version verfügbar sein.
        </p>
      </div>
    `;

    const app = document.getElementById('app');
    if (app) app.innerHTML = html;
  }

  /**
   * Rendert Kampfansicht
   */
  function renderCombat(character) {
    renderPlaceholder('Kampfbereich', 'Detaillierte Kampfverwaltung');
  }

  /**
   * Rendert Inventaransicht
   */
  function renderInventory(character) {
    renderPlaceholder('Inventar', 'Detaillierte Inventarverwaltung');
  }

  /**
   * Rendert Notizansicht
   */
  function renderNotes(character) {
    renderPlaceholder('Questnotizen', 'Erweiterte Notiz-Features');
  }

  /**
   * Rendert Einstellungsansicht
   */
  function renderSettings(character) {
    renderPlaceholder('Einstellungen', 'App-Einstellungen und Konfiguration');
  }

  /**
   * Rendert Verlaufsansicht
   */
  function renderHistory(character) {
    const app = document.getElementById('app');
    if (!app) return;

    const transactions = DndTransaction.getHistory().slice(-20);

    let html = `
      <div style="padding: 20px; max-width: 800px; margin: 0 auto;">
        <div style="margin-bottom: 20px;">
          <button onclick="DndNav.toDashboard()" style="padding: 8px 16px; margin-right: 8px;">← Zurück</button>
          <button onclick="DndNav.toDashboard()" style="padding: 8px 16px;">📊 Dashboard</button>
        </div>
        <h2>Änderungsverlauf</h2>
    `;

    if (transactions.length === 0) {
      html += '<p style="color: var(--text-secondary);">Kein Verlauf vorhanden.</p>';
    } else {
      html += '<div style="border-top: 1px solid var(--border-light);">';

      transactions.reverse().forEach(t => {
        html += `
          <div style="padding: 12px 0; border-bottom: 1px solid var(--border-light);">
            <div style="font-weight: bold; color: var(--text-primary);">
              ${DndUtils.escapeHtml(t.description)}
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
              ${DndUtils.formatDateTime(t.timestamp)}
            </div>
          </div>
        `;
      });

      html += '</div>';
    }

    html += '</div>';
    app.innerHTML = html;
  }

  return {
    renderCombat,
    renderInventory,
    renderNotes,
    renderSettings,
    renderHistory,
    renderPlaceholder
  };
})();
