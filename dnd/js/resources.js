/* D&D Companion - Ressourcen-Manager (generisch) */

const DndResources = (() => {
  'use strict';

  /**
   * Aktualisiert eine Ressource
   */
  function updateResource(character, resourceId, newValue) {
    const resource = character.resources.find(r => r.id === resourceId);
    if (!resource) return null;

    const oldValue = resource.current;
    resource.current = DndUtils.clamp(newValue, 0, resource.maximum);

    return {
      resourceId,
      oldValue,
      newValue: resource.current,
      changed: oldValue !== resource.current
    };
  }

  /**
   * Erhöht eine Ressource
   */
  function increaseResource(character, resourceId, amount = 1) {
    const resource = character.resources.find(r => r.id === resourceId);
    if (!resource) return null;

    const newValue = DndUtils.clamp(resource.current + amount, 0, resource.maximum);
    return updateResource(character, resourceId, newValue);
  }

  /**
   * Vermindert eine Ressource
   */
  function decreaseResource(character, resourceId, amount = 1) {
    return increaseResource(character, resourceId, -amount);
  }

  /**
   * Regeneriert Ressourcen nach Regel
   */
  function regenerateResources(character, restType) {
    const regenerated = [];

    character.resources.forEach(resource => {
      if (!resource.enabled || !resource.restoreRule) return;

      if (resource.restoreRule.restores !== restType && restType !== 'all') return;

      const oldValue = resource.current;

      switch (resource.restoreRule.regenerateType) {
        case 'full':
          resource.current = resource.maximum;
          break;

        case 'partial':
          const partial = Math.ceil(resource.maximum * resource.restoreRule.regenerateAmount);
          resource.current = Math.min(resource.maximum, resource.current + partial);
          break;

        case 'fixed':
          resource.current = Math.min(resource.maximum, resource.current + resource.restoreRule.regenerateAmount);
          break;

        case 'formula':
          // Für später - custom Formeln
          break;

        case 'manual':
          // Keine automatische Regeneration
          return;

        case 'none':
          // Keine Regeneration
          return;
      }

      if (oldValue !== resource.current) {
        regenerated.push({
          id: resource.id,
          name: resource.name,
          oldValue,
          newValue: resource.current
        });
      }
    });

    return regenerated;
  }

  /**
   * Gibt alle sichtbaren Ressourcen zurück
   */
  function getVisibleResources(character) {
    return character.resources.filter(r => r.visible && r.enabled);
  }

  /**
   * Gruppiert Ressourcen nach displayGroup
   */
  function getGroupedResources(character) {
    const grouped = {};

    character.resources.forEach(resource => {
      if (!resource.visible || !resource.enabled) return;

      const group = resource.displayGroup || 'Sonstiges';
      if (!grouped[group]) {
        grouped[group] = [];
      }
      grouped[group].push(resource);
    });

    return grouped;
  }

  /**
   * Sortiert Ressourcen nach order
   */
  function sortResources(resources) {
    return [...resources].sort((a, b) => (a.order || 999) - (b.order || 999));
  }

  /**
   * Validiert Ressourcen-Werte
   */
  function validateResource(resource) {
    const errors = [];

    if (!resource.id) errors.push('Ressourcen-ID fehlt');
    if (!resource.name) errors.push('Ressourcenname fehlt');
    if (resource.current < 0) errors.push('Aktueller Wert kann nicht negativ sein');
    if (resource.current > resource.maximum) errors.push('Aktueller Wert kann Maximum nicht übersteigen');
    if (resource.maximum < 0) errors.push('Maximum kann nicht negativ sein');

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * Sucht eine Ressource
   */
  function findResource(character, resourceId) {
    return character.resources.find(r => r.id === resourceId);
  }

  /**
   * Sucht Ressourcen nach Name
   */
  function findResourceByName(character, name) {
    return character.resources.find(r => r.name.toLowerCase().includes(name.toLowerCase()));
  }

  /**
   * Erstellt eine neue Ressource
   */
  function createResource(id, name, maximum = 1, restoreRule = {}) {
    return {
      id,
      name,
      shortDescription: '',
      description: '',
      category: 'custom',
      displayGroup: 'Sonstiges',
      current: maximum,
      maximum,
      type: 'counter',
      dieSize: null,
      restoreRule: Object.assign({
        restores: 'manual',
        regenerateAmount: 0,
        regenerateType: 'manual'
      }, restoreRule),
      visible: true,
      enabled: true,
      order: 999,
      source: '',
      page: 0,
      metadata: {}
    };
  }

  /**
   * Gibt einen Ressourcen-Beschreibung für die UI
   */
  function formatResourceDisplay(resource) {
    switch (resource.type) {
      case 'counter':
        return `${resource.current}/${resource.maximum}`;

      case 'boolean':
        return resource.current ? '✓' : '○';

      case 'dice':
        return `${resource.current}d${resource.dieSize}`;

      default:
        return String(resource.current);
    }
  }

  return {
    updateResource,
    increaseResource,
    decreaseResource,
    regenerateResources,
    getVisibleResources,
    getGroupedResources,
    sortResources,
    validateResource,
    findResource,
    findResourceByName,
    createResource,
    formatResourceDisplay
  };
})();
