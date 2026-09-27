/* Reiner Was-wäre-wenn-Rechner: keine Netzwerkzugriffe und keine Broker-API. */
"use strict";

const PortfolioSim = (() => {
  const kinds = new Set(["stock", "crypto", "copy", "commodity"]);
  const cents = (value) => Math.round(Number(value) * 100);
  const eur = (value) => value / 100;
  const nonnegative = (value, label) => {
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0 || !Number.isSafeInteger(cents(n))) {
      throw new Error(`${label}: ungültiger Betrag`);
    }
    return cents(n);
  };

  function validate(data) {
    if (!data || !Array.isArray(data.positions)) throw new Error("Depotdaten fehlen");
    const keys = new Set();
    for (const p of data.positions) {
      if (!p.symbol || !kinds.has(p.kind) || nonnegative(p.value_eur, p.symbol) <= 0) {
        throw new Error("Ungültige Depotposition");
      }
      const key = `${p.kind}:${p.symbol.toUpperCase()}`;
      if (keys.has(key)) throw new Error(`Doppelte Position: ${p.symbol}`);
      keys.add(key);
    }
    nonnegative(data.cash_eur, "Cash");
    return true;
  }

  function simulate(data, sells = [], buys = [], feeBps = 20, shocks = {}) {
    validate(data);
    const fee = Number(feeBps);
    if (!Number.isInteger(fee) || fee < 0 || fee > 1000) {
      throw new Error("Kosten müssen zwischen 0 und 10 % liegen");
    }
    const positions = new Map(data.positions.map(p => [
      `${p.kind}:${p.symbol.toUpperCase()}`,
      { symbol: p.symbol, kind: p.kind, valueCents: cents(p.value_eur) }
    ]));
    let cash = cents(data.cash_eur);
    let costs = 0;
    const baseCents = cash + [...positions.values()].reduce((s, p) => s + p.valueCents, 0);
    for (const row of sells) {
      const key = `${row.kind}:${String(row.symbol || "").toUpperCase()}`;
      const p = positions.get(key);
      if (!p) throw new Error(`Verkauf: ${row.symbol} ist nicht im Depot`);
      const amount = nonnegative(row.amount_eur, `Verkauf ${row.symbol}`);
      if (amount > p.valueCents) throw new Error(`Verkauf ${row.symbol} übersteigt Bestand`);
      const charge = Math.round(amount * fee / 10000);
      p.valueCents -= amount;
      cash += amount - charge;
      costs += charge;
    }
    for (const row of buys) {
      const symbol = String(row.symbol || "").trim().toUpperCase();
      if (!/^[A-Z0-9._-]{1,24}$/.test(symbol) || !kinds.has(row.kind) || row.kind === "copy") {
        throw new Error("Neukauf braucht ein gültiges Symbol und Asset-Typ");
      }
      const amount = nonnegative(row.amount_eur, `Kauf ${symbol}`);
      if (amount === 0) continue;
      const key = `${row.kind}:${symbol}`;
      if ([...positions.values()].some(p => p.symbol.toUpperCase() === symbol && p.kind !== row.kind)) {
        throw new Error(`Asset-Typ für ${symbol} ist nicht eindeutig`);
      }
      const charge = Math.round(amount * fee / 10000);
      if (amount + charge > cash) throw new Error(`Für ${symbol} reicht das fiktive Cash nicht`);
      cash -= amount + charge;
      costs += charge;
      const p = positions.get(key) || { symbol, kind: row.kind, valueCents: 0 };
      p.valueCents += amount;
      positions.set(key, p);
    }
    const active = [...positions.values()].filter(p => p.valueCents > 0);
    const currentCents = cash + active.reduce((s, p) => s + p.valueCents, 0);
    if (currentCents !== baseCents - costs) throw new Error("Bilanzgleichung verletzt");
    const stress = (items, cashCents) => {
      let total = cashCents;
      for (const p of items) {
        const change = Number(shocks[p.kind] ?? 0);
        if (!Number.isFinite(change) || change < -100 || change > 1000) {
          throw new Error(`Ungültiger Stresswert für ${p.kind}`);
        }
        total += Math.round(p.valueCents * (1 + change / 100));
      }
      return total;
    };
    const original = data.positions.map(p => ({...p, valueCents: cents(p.value_eur)}));
    const categories = {};
    for (const p of active) categories[p.kind] = (categories[p.kind] || 0) + p.valueCents;
    const largest = active.reduce((m, p) => Math.max(m, p.valueCents), 0);
    return {
      base_eur: eur(baseCents), current_eur: eur(currentCents), cash_eur: eur(cash),
      costs_eur: eur(costs), baseline_stress_eur: eur(stress(original, cents(data.cash_eur))),
      proposed_stress_eur: eur(stress(active, cash)),
      largest_weight_pct: currentCents ? 100 * largest / currentCents : 0,
      categories: Object.fromEntries(Object.entries(categories).map(([k,v]) => [k, eur(v)])),
      positions: active.map(p => ({symbol:p.symbol, kind:p.kind, value_eur:eur(p.valueCents)}))
    };
  }
  return {validate, simulate};
})();

if (typeof module !== "undefined") module.exports = PortfolioSim;
