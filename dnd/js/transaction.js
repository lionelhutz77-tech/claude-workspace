/* D&D Companion - Transaktionslogik und Undo-System */

const DndTransaction = (() => {
  'use strict';

  const MAX_HISTORY = 100;
  let history = [];
  let currentCharacter = null;

  /**
   * Initialisiert das Transaktionssystem
   */
  function init(character) {
    currentCharacter = DndUtils.deepClone(character);
    history = DndStorage.loadHistory() || [];
  }

  /**
   * Erstellt einen Transaktionseintrag
   */
  function createTransaction(action, cause, description, before, after, userAction = '', notes = '') {
    return {
      id: DndUtils.generateId(),
      transactionId: DndUtils.generateId(),
      originTransactionId: null,
      timestamp: DndUtils.getCurrentTimestamp(),
      action,
      cause,
      actionType: action,
      description,
      before: DndUtils.deepClone(before),
      after: DndUtils.deepClone(after),
      userAction,
      undoable: true,
      undoReference: null,
      notes
    };
  }

  /**
   * Protokolliert eine Transaktion
   */
  function logTransaction(transaction) {
    history.push(transaction);

    if (history.length > MAX_HISTORY) {
      history = history.slice(-MAX_HISTORY);
    }

    DndStorage.saveHistory(history);
    return transaction;
  }

  /**
   * Führt eine Schaden-Transaktion durch
   */
  function transactionDamage(currentCharacter, damage, notes = '') {
    const before = {
      hp: currentCharacter.hitpoints.current,
      tempHp: currentCharacter.hitpoints.temporary
    };

    const calc = DndUtils.calculateDamage(
      damage,
      currentCharacter.hitpoints.current,
      currentCharacter.hitpoints.max,
      currentCharacter.hitpoints.temporary
    );

    currentCharacter.hitpoints.current = calc.newHp;
    currentCharacter.hitpoints.temporary = calc.newTempHp;

    const after = {
      hp: currentCharacter.hitpoints.current,
      tempHp: currentCharacter.hitpoints.temporary
    };

    const description = `Schaden ${damage} (${calc.damageToTemp} von Temp, ${calc.damageToHp} regulär)`;

    const transaction = createTransaction(
      'damage',
      'player-action',
      description,
      before,
      after,
      'Schaden eingegeben',
      notes
    );

    return logTransaction(transaction);
  }

  /**
   * Führt eine Heilungs-Transaktion durch
   */
  function transactionHealing(currentCharacter, healing, notes = '') {
    const before = {
      hp: currentCharacter.hitpoints.current
    };

    const calc = DndUtils.calculateHealing(
      healing,
      currentCharacter.hitpoints.current,
      currentCharacter.hitpoints.max
    );

    currentCharacter.hitpoints.current = calc.newHp;

    const after = {
      hp: currentCharacter.hitpoints.current
    };

    const description = `Heilung ${calc.healing}${calc.overkill > 0 ? ` (${calc.overkill} überschüssig)` : ''}`;

    const transaction = createTransaction(
      'healing',
      'player-action',
      description,
      before,
      after,
      'Heilung eingetragen',
      notes
    );

    return logTransaction(transaction);
  }

  /**
   * Heiltrank-Transaktion (komplexe Transaktion)
   */
  function transactionPotion(currentCharacter, healAmount, potionName = 'Heiltrank', notes = '') {
    // Finde den Heiltrank im Inventar
    const healingPotionIndex = currentCharacter.inventory.consumables.findIndex(
      item => item.name.toLowerCase().includes('trank') || item.name.toLowerCase().includes('potion')
    );

    const before = {
      hp: currentCharacter.hitpoints.current,
      potionQuantity: healingPotionIndex >= 0 ? currentCharacter.inventory.consumables[healingPotionIndex].quantity : 0
    };

    const calc = DndUtils.calculateHealing(
      healAmount,
      currentCharacter.hitpoints.current,
      currentCharacter.hitpoints.max
    );

    currentCharacter.hitpoints.current = calc.newHp;

    if (healingPotionIndex >= 0) {
      currentCharacter.inventory.consumables[healingPotionIndex].quantity--;
    }

    const after = {
      hp: currentCharacter.hitpoints.current,
      potionQuantity: healingPotionIndex >= 0 ? currentCharacter.inventory.consumables[healingPotionIndex].quantity : 0
    };

    const description = `${potionName} verwendet (+${calc.healing} HP, Anzahl: ${after.potionQuantity})`;

    const transaction = createTransaction(
      'potion_used',
      'player-action',
      description,
      before,
      after,
      'Heiltrank benutzt',
      notes
    );

    transaction.metadata = {
      potionName,
      healAmount: calc.healing
    };

    return logTransaction(transaction);
  }

  /**
   * Temp-HP-Transaktion
   */
  function transactionTempHp(currentCharacter, tempHp, notes = '') {
    const before = {
      tempHp: currentCharacter.hitpoints.temporary
    };

    const newTempHp = Math.max(currentCharacter.hitpoints.temporary, tempHp);
    currentCharacter.hitpoints.temporary = newTempHp;

    const after = {
      tempHp: currentCharacter.hitpoints.temporary
    };

    const description = `Temp HP auf ${newTempHp} gesetzt${tempHp > before.tempHp ? ` (vorher: ${before.tempHp})` : ''}`;

    const transaction = createTransaction(
      'tempHp',
      'player-action',
      description,
      before,
      after,
      'Temporäre HP eingestellt',
      notes
    );

    return logTransaction(transaction);
  }

  /**
   * Ressourcen-Transaktion
   */
  function transactionResource(currentCharacter, resourceId, change, notes = '') {
    const resource = currentCharacter.resources.find(r => r.id === resourceId);
    if (!resource) return null;

    const before = {
      resourceName: resource.name,
      resourceValue: resource.current
    };

    resource.current = DndUtils.clamp(resource.current + change, 0, resource.maximum);

    const after = {
      resourceValue: resource.current
    };

    const changeSign = change > 0 ? '+' : '';
    const description = `${resource.name}: ${changeSign}${change} (${after.resourceValue}/${resource.maximum})`;

    const transaction = createTransaction(
      'resource_used',
      'player-action',
      description,
      before,
      after,
      `Ressource ${resource.name} verändert`,
      notes
    );

    transaction.metadata = {
      resourceId,
      resourceName: resource.name,
      change
    };

    return logTransaction(transaction);
  }

  /**
   * Manöver-Transaktion
   */
  function transactionManeuver(currentCharacter, maneuverName, resourceId = 'superiority_dice', notes = '') {
    const resource = currentCharacter.resources.find(r => r.id === resourceId);
    if (!resource || resource.current < 1) {
      return null;
    }

    const before = {
      maneuverName,
      resourceValue: resource.current
    };

    resource.current--;

    const after = {
      resourceValue: resource.current
    };

    const description = `${maneuverName} eingesetzt (${resource.name}: ${after.resourceValue}/${resource.maximum})`;

    const transaction = createTransaction(
      'maneuver_used',
      'player-action',
      description,
      before,
      after,
      `Manöver ${maneuverName} verwendet`,
      notes
    );

    transaction.metadata = {
      maneuverName,
      resourceId
    };

    return logTransaction(transaction);
  }

  /**
   * Zustand-Transaktion
   */
  function transactionCondition(currentCharacter, conditionId, apply = true, notes = '') {
    const condition = currentCharacter.conditions.find(c => c.id === conditionId);

    const before = {
      conditions: DndUtils.deepClone(currentCharacter.conditions)
    };

    if (apply && !condition) {
      currentCharacter.conditions.push({
        id: conditionId,
        active: true,
        durationRounds: null,
        notes: notes
      });
    } else if (!apply && condition) {
      currentCharacter.conditions = currentCharacter.conditions.filter(c => c.id !== conditionId);
    }

    const after = {
      conditions: DndUtils.deepClone(currentCharacter.conditions)
    };

    const action = apply ? 'angewendet' : 'entfernt';
    const description = `Zustand ${action}: ${conditionId}`;

    const transaction = createTransaction(
      apply ? 'condition_applied' : 'condition_removed',
      'player-action',
      description,
      before,
      after,
      `Zustand ${action}`,
      notes
    );

    return logTransaction(transaction);
  }

  /**
   * Rückgängig-Funktion
   */
  function undo(transactionId, characterRef) {
    const transaction = history.find(t => t.id === transactionId);
    if (!transaction || !transaction.undoable) {
      return null;
    }

    // Stelle die Werte im globalen currentCharacter wieder her
    if (transaction.action === 'damage') {
      currentCharacter.hitpoints.current = transaction.before.hp;
      currentCharacter.hitpoints.temporary = transaction.before.tempHp;
    } else if (transaction.action === 'healing') {
      currentCharacter.hitpoints.current = transaction.before.hp;
    } else if (transaction.action === 'tempHp') {
      currentCharacter.hitpoints.temporary = transaction.before.tempHp;
    } else if (transaction.action === 'resource_used') {
      const resource = currentCharacter.resources.find(r => r.name === transaction.before.resourceName);
      if (resource) {
        resource.current = transaction.before.resourceValue;
      }
    } else if (transaction.action === 'maneuver_used') {
      const resource = currentCharacter.resources.find(r => r.id === transaction.metadata.resourceId);
      if (resource) {
        resource.current = transaction.before.resourceValue;
      }
    } else if (transaction.action === 'potion_used') {
      currentCharacter.hitpoints.current = transaction.before.hp;
      const potion = currentCharacter.inventory.consumables.find(
        p => p.name.toLowerCase().includes('trank')
      );
      if (potion) {
        potion.quantity = transaction.before.potionQuantity;
      }
    } else if (transaction.action === 'condition_applied' || transaction.action === 'condition_removed') {
      currentCharacter.conditions = DndUtils.deepClone(transaction.before.conditions);
    }

    // Falls ein characterRef übergeben wurde (z.B. in Tests), aktualisiere diesen auch
    if (characterRef) {
      if (transaction.action === 'damage') {
        characterRef.hitpoints.current = transaction.before.hp;
        characterRef.hitpoints.temporary = transaction.before.tempHp;
      } else if (transaction.action === 'healing') {
        characterRef.hitpoints.current = transaction.before.hp;
      } else if (transaction.action === 'tempHp') {
        characterRef.hitpoints.temporary = transaction.before.tempHp;
      } else if (transaction.action === 'resource_used') {
        const resource = characterRef.resources.find(r => r.name === transaction.before.resourceName);
        if (resource) {
          resource.current = transaction.before.resourceValue;
        }
      } else if (transaction.action === 'maneuver_used') {
        const resource = characterRef.resources.find(r => r.id === transaction.metadata.resourceId);
        if (resource) {
          resource.current = transaction.before.resourceValue;
        }
      } else if (transaction.action === 'potion_used') {
        characterRef.hitpoints.current = transaction.before.hp;
        const potion = characterRef.inventory.consumables.find(
          p => p.name.toLowerCase().includes('trank')
        );
        if (potion) {
          potion.quantity = transaction.before.potionQuantity;
        }
      } else if (transaction.action === 'condition_applied' || transaction.action === 'condition_removed') {
        characterRef.conditions = DndUtils.deepClone(transaction.before.conditions);
      }
    }

    // Erstelle Undo-Transaktion
    const undoTransaction = createTransaction(
      'undo',
      'player-action',
      `Undo: ${transaction.description}`,
      transaction.after,
      transaction.before,
      'Aktion rückgängig gemacht',
      ''
    );

    undoTransaction.undoReference = transactionId;
    undoTransaction.originTransactionId = transaction.id;

    // Markiere die Original-Transaktion als rückgängig gemacht
    transaction.undoable = false;

    logTransaction(undoTransaction);

    // Speichere den Charakter und den Verlauf persistent
    DndStorage.saveCharacter(currentCharacter);
    DndStorage.saveHistory(history);

    return undoTransaction;
  }

  /**
   * Gibt die letzten N Transaktionen zurück
   */
  function getRecentTransactions(count = 10) {
    return history.slice(-count).reverse();
  }

  /**
   * Gibt den vollständigen Verlauf zurück
   */
  function getHistory() {
    return DndUtils.deepClone(history);
  }

  /**
   * Löscht den Verlauf (vorsichtig!)
   */
  function clearHistory() {
    history = [];
    DndStorage.saveHistory([]);
  }

  /**
   * Gibt Statistiken zum Verlauf
   */
  function getHistoryStats() {
    const stats = {
      totalEntries: history.length,
      actionCounts: {},
      dateRange: null
    };

    if (history.length > 0) {
      stats.dateRange = {
        first: history[0].timestamp,
        last: history[history.length - 1].timestamp
      };

      history.forEach(t => {
        stats.actionCounts[t.action] = (stats.actionCounts[t.action] || 0) + 1;
      });
    }

    return stats;
  }

  return {
    init,
    createTransaction,
    logTransaction,
    transactionDamage,
    transactionHealing,
    transactionPotion,
    transactionTempHp,
    transactionResource,
    transactionManeuver,
    transactionCondition,
    undo,
    getRecentTransactions,
    getHistory,
    clearHistory,
    getHistoryStats,
    get currentCharacter() {
      return currentCharacter;
    },
    set currentCharacter(value) {
      currentCharacter = value;
    }
  };
})();
