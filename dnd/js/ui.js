/* D&D Companion - UI-Rendering und Interaktionen */

const DndUI = (() => {
  'use strict';

  const app = document.getElementById('app');
  let currentCharacter = null;
  let currentView = 'dashboard';

  /**
   * Rendert das Dashboard
   */
  function renderDashboard(character) {
    currentCharacter = character;

    const html = `
      <div class="dashboard">
        <!-- Header -->
        <div class="dashboard-header">
          <div class="character-title">
            <h1 data-action="editName" style="cursor: pointer; user-select: none; padding: 8px; border-radius: 4px; hover:background: var(--bg-secondary);">
              ${DndUtils.escapeHtml(character.meta.name || 'Ohne Namen')}
            </h1>
          </div>
          <div class="character-info">
            <div style="cursor: pointer; padding: 4px 8px; border-radius: 4px;" data-action="editClass">
              <strong>${DndUtils.escapeHtml(character.basics.class.name || 'Klasse')}</strong>
            </div>
            <div style="cursor: pointer; padding: 4px 8px; border-radius: 4px;" data-action="editSubclass">
              ${DndUtils.escapeHtml(character.basics.class.subclass || 'Unterklasse')}
            </div>
            <div style="cursor: pointer; padding: 4px 8px; border-radius: 4px;" data-action="editLevel">
              Stufe ${character.basics.class.level}
            </div>
          </div>
        </div>

        <!-- HP-Bereich -->
        <div class="hp-section">
          <div class="hp-header">Trefferpunkte</div>

          <div class="hp-display">
            <div class="hp-value">
              <span class="hp-value-current">${character.hitpoints.current}</span>
              <span class="hp-value-max" data-action="editMaxHp" style="cursor: pointer; user-select: none;">/ ${character.hitpoints.max}</span>
            </div>

            <div class="hp-bar">
              <div class="hp-bar-fill ${DndUtils.getHpClass(character.hitpoints.current, character.hitpoints.max)}"
                   style="width: ${(character.hitpoints.current / character.hitpoints.max * 100)}%"></div>
            </div>
          </div>

          ${character.hitpoints.temporary > 0 ? `
            <div class="temp-hp">
              <span class="temp-hp-label">Temporäre HP</span>
              <span class="temp-hp-value">${character.hitpoints.temporary}</span>
            </div>
          ` : ''}

          <div class="hp-actions">
            <button data-action="damage">⚔ Schaden</button>
            <button data-action="healing">❤ Heilung</button>
            <button data-action="tempHp">🛡 Temp HP</button>
            <button data-action="fullHeal">✨ Vollständig</button>
          </div>
        </div>

        <!-- Schnell-Stats -->
        <div class="quick-stats">
          <div class="stat-box" data-action="editAc">
            <div class="stat-label">Rüstungsklasse</div>
            <div class="stat-value">${character.ac}</div>
          </div>
          <div class="stat-box" data-action="editInitiative">
            <div class="stat-label">Initiative</div>
            <div class="stat-value">${character.initiative > 0 ? '+' : ''}${character.initiative}</div>
          </div>
          <div class="stat-box" data-action="editSpeed">
            <div class="stat-label">Bewegung</div>
            <div class="stat-value">${character.speed} ft</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Pass. Wahrn.</div>
            <div class="stat-value">${10 + (character.abilities.wisdom?.modifier || 0)}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Inspiration</div>
            <div class="stat-value">${character.inspiration ? '✓' : '○'}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Erschöpfung</div>
            <div class="stat-value">${character.exhaustion}/6</div>
          </div>
        </div>

        <!-- Aktive Zustände -->
        ${character.conditions && character.conditions.length > 0 ? `
          <div class="active-conditions">
            <div class="conditions-header">Aktive Zustände</div>
            <div class="condition-chips">
              ${character.conditions.slice(0, 5).map(c => `
                <div class="condition-chip" data-condition-id="${c.id}">
                  <span>${DndUtils.escapeHtml(c.id)}</span>
                </div>
              `).join('')}
              ${character.conditions.length > 5 ? `<div class="condition-chip">+${character.conditions.length - 5}</div>` : ''}
            </div>
          </div>
        ` : ''}

        <!-- Ressourcen -->
        <div class="resources-section">
          <div class="resource-header">Ressourcen</div>
          <div>
            ${character.resources.filter(r => r.visible && r.enabled).map(resource => `
              <div class="resource-item">
                <div class="resource-name">${DndUtils.escapeHtml(resource.name)}</div>
                <div class="resource-value">
                  <span>${DndResources.formatResourceDisplay(resource)}</span>
                  <div class="resource-controls">
                    <button data-action="resource-dec" data-resource-id="${resource.id}">−</button>
                    <button data-action="resource-inc" data-resource-id="${resource.id}">+</button>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Zuletzt verwendet -->
        <div class="recent-action">
          <div class="recent-action-text">
            <strong>Zuletzt:</strong> <span id="recent-action-text">Keine Aktion</span>
          </div>
          <button class="undo-button" data-action="undo" style="display: none;">↶ Rückgängig</button>
        </div>

        <!-- Favoriten -->
        <div class="favorites-section">
          <div class="favorites-grid">
            <button class="favorite-button" data-action="damage">⚔ Schaden</button>
            <button class="favorite-button" data-action="healing">❤ Heilung</button>
            <button class="favorite-button" data-action="tempHp">🛡 Temp HP</button>
            <button class="favorite-button" data-action="potion">⚗ Heiltrank</button>
            <button class="favorite-button" data-action="maneuver">🗡 Manöver</button>
            <button class="favorite-button" data-action="condition">😵 Zustände</button>
            <button class="favorite-button" data-action="inventory">🎒 Inventar</button>
            <button class="favorite-button" data-action="shortRest">🏕 K. Rast</button>
            <button class="favorite-button" data-action="longRest">🛌 L. Rast</button>
            <button class="favorite-button" data-action="history">📜 Verlauf</button>
          </div>
        </div>
      </div>

      <!-- Navigation Bar -->
      <div class="nav-bar">
        <button class="nav-button active" data-view="dashboard">📊 Dashboard</button>
        <button class="nav-button" data-view="combat">⚔ Kampf</button>
        <button class="nav-button" data-view="spells">✨ Zauber</button>
        <button class="nav-button" data-view="inventory">🎒 Inventar</button>
        <button class="nav-button" data-view="notes">📝 Notizen</button>
        <button class="nav-button" data-view="settings">⚙ Mehr</button>
      </div>
    `;

    app.innerHTML = html;
    attachDashboardEvents(character);
  }

  /**
   * Befestigt Events auf dem Dashboard
   */
  function attachDashboardEvents(character) {
    // Action-Buttons
    DndUtils.on(app, 'click', '[data-action]', function() {
      const action = this.dataset.action;
      handleAction(action, character);
    });

    // Resource-Controls
    DndUtils.on(app, 'click', '[data-resource-id]', function() {
      const resourceId = this.dataset.resourceId;
      const action = this.dataset.action;
      handleResourceAction(action, resourceId, character);
    });

    // Navigation
    DndUtils.on(app, 'click', '[data-view]', function() {
      const view = this.dataset.view;
      switchView(view, character);
    });
  }

  /**
   * Behandelt Action-Klicks
   */
  async function handleAction(action, character) {
    switch (action) {
      case 'damage':
        handleDamage(character);
        break;

      case 'healing':
        handleHealing(character);
        break;

      case 'tempHp':
        handleTempHp(character);
        break;

      case 'fullHeal':
        handleFullHeal(character);
        break;

      case 'undo':
        handleUndo(character);
        break;

      case 'potion':
        handlePotion(character);
        break;

      case 'shortRest':
        handleShortRest(character);
        break;

      case 'longRest':
        handleLongRest(character);
        break;

      case 'history':
        switchView('history', character);
        break;

      // Edit Actions
      case 'editName':
        handleEditName(character);
        break;

      case 'editClass':
        handleEditClass(character);
        break;

      case 'editSubclass':
        handleEditSubclass(character);
        break;

      case 'editLevel':
        handleEditLevel(character);
        break;

      case 'editAc':
        handleEditAc(character);
        break;

      case 'editInitiative':
        handleEditInitiative(character);
        break;

      case 'editSpeed':
        handleEditSpeed(character);
        break;

      case 'editMaxHp':
        handleEditMaxHp(character);
        break;

      case 'editAbility':
        const ability = this.dataset.ability;
        if (ability) handleEditAbility(character, ability);
        break;
    }
  }

  /**
   * Behandelt Schaden
   */
  async function handleDamage(character) {
    const damage = await DndModal.inputDialog(
      'Schaden eintragen',
      'Schadenbetrag:',
      '0',
      'number'
    );

    if (damage !== null) {
      const amount = parseInt(damage) || 0;
      if (amount > 0) {
        DndTransaction.transactionDamage(character, amount);
        DndStorage.saveCharacter(character);
        renderDashboard(character);
        DndUtils.showNotification(`${amount} Schaden eingetragen!`);
      }
    }
  }

  /**
   * Behandelt Heilung
   */
  async function handleHealing(character) {
    const healing = await DndModal.inputDialog(
      'Heilung eintragen',
      'Heilungsbetrag:',
      '0',
      'number'
    );

    if (healing !== null) {
      const amount = parseInt(healing) || 0;
      if (amount > 0) {
        DndTransaction.transactionHealing(character, amount);
        DndStorage.saveCharacter(character);
        renderDashboard(character);
        DndUtils.showNotification(`${amount} HP Heilung!`);
      }
    }
  }

  /**
   * Behandelt temporäre HP
   */
  async function handleTempHp(character) {
    const tempHp = await DndModal.inputDialog(
      'Temporäre HP',
      'Temporäre Trefferpunkte:',
      String(character.hitpoints.temporary),
      'number'
    );

    if (tempHp !== null) {
      const amount = parseInt(tempHp) || 0;
      if (amount >= 0) {
        DndTransaction.transactionTempHp(character, amount);
        DndStorage.saveCharacter(character);
        renderDashboard(character);
        DndUtils.showNotification(`Temp HP auf ${amount} gesetzt!`);
      }
    }
  }

  /**
   * Behandelt volle Heilung
   */
  async function handleFullHeal(character) {
    const confirmed = await DndModal.confirmDialog(
      'Vollständig heilen?',
      'Setzt Trefferpunkte auf Maximum',
      `${character.hitpoints.current} → ${character.hitpoints.max}`
    );

    if (confirmed) {
      const healing = character.hitpoints.max - character.hitpoints.current;
      if (healing > 0) {
        DndTransaction.transactionHealing(character, healing);
        DndStorage.saveCharacter(character);
        renderDashboard(character);
        DndUtils.showNotification('Vollständig geheilt!');
      }
    }
  }

  /**
   * Behandelt Undo
   */
  function handleUndo(character) {
    const recent = DndTransaction.getRecentTransactions(1);
    if (recent.length > 0) {
      DndTransaction.undo(recent[0].id);
      DndStorage.saveCharacter(character);
      renderDashboard(character);
      DndUtils.showNotification('Aktion rückgängig gemacht');
    }
  }

  /**
   * Behandelt Heiltrank
   */
  async function handlePotion(character) {
    DndUtils.showNotification('Heiltrank-Funktion folgt...');
  }

  /**
   * Behandelt kurze Rast
   */
  async function handleShortRest(character) {
    const confirm = await DndModal.confirmDialog(
      'Kurze Rast',
      'Trefferwürfel werden wiederhergestellt',
      `Verfügbar: ${character.hitpoints.hd.current}/${character.hitpoints.hd.max}`
    );

    if (confirm) {
      DndResources.regenerateResources(character, 'shortRest');
      DndStorage.saveCharacter(character);
      renderDashboard(character);
      DndUtils.showNotification('Kurze Rast abgeschlossen!');
    }
  }

  /**
   * Behandelt lange Rast
   */
  async function handleLongRest(character) {
    const confirm = await DndModal.confirmDialog(
      'Lange Rast',
      'Alle Ressourcen werden wiederhergestellt',
      `HP: ${character.hitpoints.current} → ${character.hitpoints.max}`
    );

    if (confirm) {
      character.hitpoints.current = character.hitpoints.max;
      DndResources.regenerateResources(character, 'longRest');
      character.exhaustion = Math.max(0, character.exhaustion - 1);
      DndStorage.saveCharacter(character);
      renderDashboard(character);
      DndUtils.showNotification('Lange Rast abgeschlossen!');
    }
  }

  /**
   * Behandelt Ressourcen-Aktionen
   */
  function handleResourceAction(action, resourceId, character) {
    const change = action === 'resource-inc' ? 1 : -1;
    DndTransaction.transactionResource(character, resourceId, change);
    DndStorage.saveCharacter(character);
    renderDashboard(character);
  }

  /**
   * Wechselt die Ansicht
   */
  function switchView(view, character) {
    currentView = view;

    if (view === 'dashboard') {
      renderDashboard(character);
    } else if (view === 'combat') {
      renderCombatView(character);
    } else if (view === 'inventory') {
      renderInventoryView(character);
    } else if (view === 'notes') {
      renderNotesView(character);
    } else if (view === 'settings') {
      renderSettingsView(character);
    } else if (view === 'history') {
      renderHistoryView(character);
    }
  }

  /**
   * Rendert Kampfansicht (Placeholder)
   */
  function renderCombatView(character) {
    const html = '<div style="padding: 20px;"><h2>Kampfbereich</h2><p>Kampffeatures folgen...</p></div>';
    app.innerHTML = html;
  }

  /**
   * Rendert Inventaransicht (Placeholder)
   */
  function renderInventoryView(character) {
    const html = '<div style="padding: 20px;"><h2>Inventar</h2><p>Inventarfeatures folgen...</p></div>';
    app.innerHTML = html;
  }

  /**
   * Rendert Notizansicht (Placeholder)
   */
  function renderNotesView(character) {
    const html = '<div style="padding: 20px;"><h2>Questnotizen</h2><p>Notiz-Features folgen...</p></div>';
    app.innerHTML = html;
  }

  /**
   * Rendert Einstellungsansicht (Placeholder)
   */
  function renderSettingsView(character) {
    const html = '<div style="padding: 20px;"><h2>Einstellungen</h2><p>Einstellungs-Features folgen...</p></div>';
    app.innerHTML = html;
  }

  /**
   * Rendert Verlaufsansicht (Placeholder)
   */
  function renderHistoryView(character) {
    const html = '<div style="padding: 20px;"><h2>Änderungsverlauf</h2><p>Verlaufs-Features folgen...</p></div>';
    app.innerHTML = html;
  }

  // ===== EDIT HANDLER =====

  /**
   * Name bearbeiten
   */
  async function handleEditName(character) {
    const name = await DndModal.inputDialog(
      'Charaktername',
      'Name:',
      character.meta.name || '',
      'text'
    );
    if (name !== null) {
      character.meta.name = name || 'Charakter ohne Namen';
      DndStorage.saveCharacter(character);
      renderDashboard(character);
    }
  }

  /**
   * Klasse bearbeiten
   */
  async function handleEditClass(character) {
    const className = await DndModal.inputDialog(
      'Klasse',
      'Klasse:',
      character.basics.class.name || '',
      'text'
    );
    if (className !== null) {
      character.basics.class.name = className;
      DndStorage.saveCharacter(character);
      renderDashboard(character);
    }
  }

  /**
   * Unterklasse bearbeiten
   */
  async function handleEditSubclass(character) {
    const subclass = await DndModal.inputDialog(
      'Unterklasse',
      'Unterklasse:',
      character.basics.class.subclass || '',
      'text'
    );
    if (subclass !== null) {
      character.basics.class.subclass = subclass;
      DndStorage.saveCharacter(character);
      renderDashboard(character);
    }
  }

  /**
   * Stufe bearbeiten
   */
  async function handleEditLevel(character) {
    const level = await DndModal.inputDialog(
      'Stufe',
      'Stufe:',
      String(character.basics.class.level),
      'number'
    );
    if (level !== null) {
      const newLevel = Math.max(1, Math.min(20, parseInt(level) || 1));
      character.basics.class.level = newLevel;
      DndStorage.saveCharacter(character);
      renderDashboard(character);
    }
  }

  /**
   * AC bearbeiten
   */
  async function handleEditAc(character) {
    const ac = await DndModal.inputDialog(
      'Rüstungsklasse',
      'AC:',
      String(character.ac),
      'number'
    );
    if (ac !== null) {
      character.ac = Math.max(1, parseInt(ac) || 10);
      DndStorage.saveCharacter(character);
      renderDashboard(character);
    }
  }

  /**
   * Initiative bearbeiten
   */
  async function handleEditInitiative(character) {
    const initiative = await DndModal.inputDialog(
      'Initiative',
      'Initiative Modifikator:',
      String(character.initiative),
      'number'
    );
    if (initiative !== null) {
      character.initiative = parseInt(initiative) || 0;
      DndStorage.saveCharacter(character);
      renderDashboard(character);
    }
  }

  /**
   * Bewegungsgeschwindigkeit bearbeiten
   */
  async function handleEditSpeed(character) {
    const speed = await DndModal.inputDialog(
      'Bewegungsgeschwindigkeit',
      'Fuß pro Runde:',
      String(character.speed),
      'number'
    );
    if (speed !== null) {
      character.speed = Math.max(0, parseInt(speed) || 30);
      DndStorage.saveCharacter(character);
      renderDashboard(character);
    }
  }

  /**
   * Max HP bearbeiten
   */
  async function handleEditMaxHp(character) {
    const maxHp = await DndModal.inputDialog(
      'Maximale Trefferpunkte',
      'Max HP:',
      String(character.hitpoints.max),
      'number'
    );
    if (maxHp !== null) {
      const newMax = Math.max(1, parseInt(maxHp) || 10);
      character.hitpoints.max = newMax;
      // Stelle sicher, dass aktuell HP nicht überschritten wird
      character.hitpoints.current = Math.min(character.hitpoints.current, newMax);
      DndStorage.saveCharacter(character);
      renderDashboard(character);
    }
  }

  /**
   * Attribut bearbeiten
   */
  async function handleEditAbility(character, ability) {
    const score = await DndModal.inputDialog(
      `${ability.charAt(0).toUpperCase() + ability.slice(1)}`,
      'Attributswert:',
      String(character.abilities[ability]?.score || 10),
      'number'
    );
    if (score !== null) {
      const newScore = Math.max(1, Math.min(20, parseInt(score) || 10));
      if (character.abilities[ability]) {
        character.abilities[ability].score = newScore;
        character.abilities[ability].modifier = Math.floor((newScore - 10) / 2);
      }
      DndStorage.saveCharacter(character);
      renderDashboard(character);
    }
  }

  return {
    renderDashboard,
    attachDashboardEvents,
    handleAction,
    switchView,
    get currentView() {
      return currentView;
    }
  };
})();
