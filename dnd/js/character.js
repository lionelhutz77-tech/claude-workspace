/* D&D Companion - Charakterdatenmodell */

const DndCharacter = (() => {
  'use strict';

  /**
   * Standard-Charaktervorlage
   */
  function getDefaultTemplate() {
    return {
      meta: {
        id: DndUtils.generateId(),
        name: '',
        schemaVersion: 1,
        characterVersion: 1,
        created: DndUtils.getCurrentTimestamp(),
        lastModified: DndUtils.getCurrentTimestamp(),
        ruleset: 'dnd5e'
      },

      basics: {
        class: {
          name: '',
          level: 1,
          subclass: ''
        },
        race: '',
        background: '',
        alignment: ''
      },

      abilities: {
        strength: { score: 10, modifier: 0 },
        dexterity: { score: 10, modifier: 0 },
        constitution: { score: 10, modifier: 0 },
        intelligence: { score: 10, modifier: 0 },
        wisdom: { score: 10, modifier: 0 },
        charisma: { score: 10, modifier: 0 }
      },

      proficiency: {
        bonus: 2,
        savingThrows: [],
        skills: {},
        expertise: []
      },

      hitpoints: {
        max: 10,
        current: 10,
        temporary: 0,
        hd: {
          size: 'd8',
          current: 1,
          max: 1
        }
      },

      ac: 10,
      initiative: 0,
      speed: 30,

      inspiration: false,
      exhaustion: 0,

      resources: getDefaultResources(),
      conditions: [],
      inventory: getDefaultInventory(),
      abilities: getDefaultAbilities(),
      questNotes: {
        currentQuest: '',
        importantPersons: [],
        importantPlaces: [],
        openHints: [],
        freeNotes: ''
      }
    };
  }

  /**
   * Standard-Ressourcen
   */
  function getDefaultResources() {
    return [
      {
        id: 'superiority_dice',
        name: 'Überlegenheitswürfel',
        shortDescription: 'Würfel für Kampfmeister-Manöver',
        description: 'Werden für Kampfmeister-Manöver verwendet',
        category: 'combat',
        displayGroup: 'Kampf',
        current: 0,
        maximum: 1,
        type: 'counter',
        dieSize: 'd8',
        restoreRule: {
          restores: 'longRest',
          regenerateAmount: -1,
          regenerateType: 'full'
        },
        visible: true,
        enabled: true,
        order: 1,
        source: 'PHB',
        page: 70,
        metadata: {}
      },
      {
        id: 'inspiration',
        name: 'Inspiration',
        shortDescription: '+1d20 auf Wurf',
        description: 'Inspiration für wichtige Würfe',
        category: 'special',
        displayGroup: 'Spezial',
        current: false,
        maximum: 1,
        type: 'boolean',
        restoreRule: {
          restores: 'manual',
          regenerateAmount: 0,
          regenerateType: 'manual'
        },
        visible: true,
        enabled: true,
        order: 2,
        source: 'PHB',
        page: 125,
        metadata: {}
      },
      {
        id: 'action_surge',
        name: 'Aktionsdrang',
        shortDescription: 'Extra-Aktion',
        description: 'Zusätzliche Aktion im Kampf',
        category: 'combat',
        displayGroup: 'Kampf',
        current: 0,
        maximum: 1,
        type: 'counter',
        restoreRule: {
          restores: 'shortRest',
          regenerateAmount: -1,
          regenerateType: 'full'
        },
        visible: true,
        enabled: true,
        order: 3,
        source: 'PHB',
        page: 70,
        metadata: {}
      },
      {
        id: 'second_wind',
        name: 'Zweiter Wind',
        shortDescription: '+1d10 Heilung',
        description: 'Selbstheilung im Kampf',
        category: 'healing',
        displayGroup: 'Heilung',
        current: 0,
        maximum: 1,
        type: 'counter',
        restoreRule: {
          restores: 'shortRest',
          regenerateAmount: -1,
          regenerateType: 'full'
        },
        visible: true,
        enabled: true,
        order: 4,
        source: 'PHB',
        page: 70,
        metadata: { healAmount: 10 }
      }
    ];
  }

  /**
   * Standard-Inventar
   */
  function getDefaultInventory() {
    return {
      weapons: [],
      armor: [],
      magicalItems: [],
      consumables: [],
      other: []
    };
  }

  /**
   * Standard-Fähigkeiten
   */
  function getDefaultAbilities() {
    return {
      race: [],
      class: [],
      subclass: [],
      talents: [],
      background: [],
      other: []
    };
  }

  /**
   * Erstellt einen neuen Charakter
   */
  function create(name = '') {
    const character = getDefaultTemplate();
    character.meta.name = name;
    character.meta.created = DndUtils.getCurrentTimestamp();
    character.meta.lastModified = DndUtils.getCurrentTimestamp();
    return character;
  }

  /**
   * Aktualisiert den Modifikator für ein Attribut
   */
  function updateAbilityModifier(character, ability) {
    const score = character.abilities[ability].score;
    character.abilities[ability].modifier = Math.floor((score - 10) / 2);
    character.meta.lastModified = DndUtils.getCurrentTimestamp();
  }

  /**
   * Setzt einen Wert und aktualisiert Timestamp
   */
  function updateValue(character, path, value) {
    const keys = path.split('.');
    let obj = character;

    for (let i = 0; i < keys.length - 1; i++) {
      if (!obj[keys[i]]) obj[keys[i]] = {};
      obj = obj[keys[i]];
    }

    obj[keys[keys.length - 1]] = value;
    character.meta.lastModified = DndUtils.getCurrentTimestamp();
  }

  /**
   * Gibt einen Wert zurück
   */
  function getValue(character, path) {
    const keys = path.split('.');
    let obj = character;

    for (const key of keys) {
      obj = obj[key];
      if (obj === undefined) return undefined;
    }

    return obj;
  }

  /**
   * Validiert einen Charakter
   */
  function validate(character) {
    const validation = DndUtils.validateCharacterData(character);

    if (character.hitpoints.temporary < 0) {
      validation.errors.push('Temporäre Trefferpunkte können nicht negativ sein');
      validation.valid = false;
    }

    if (character.hitpoints.current > character.hitpoints.max) {
      validation.errors.push('Aktuelle HP können max. HP nicht übersteigen');
      validation.valid = false;
    }

    if (character.exhaustion < 0 || character.exhaustion > 6) {
      validation.errors.push('Erschöpfungsstufe muss zwischen 0 und 6 liegen');
      validation.valid = false;
    }

    return validation;
  }

  /**
   * Erstellt einen sanitierten Klon (für Export)
   */
  function clone(character) {
    return DndUtils.deepClone(character);
  }

  return {
    getDefaultTemplate,
    getDefaultResources,
    getDefaultInventory,
    getDefaultAbilities,
    create,
    updateAbilityModifier,
    updateValue,
    getValue,
    validate,
    clone
  };
})();
