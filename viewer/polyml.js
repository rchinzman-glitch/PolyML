// polyML helpers shared by the viewer and the builder.
// Mirrors python/src/polyml/core.py; keep the two in step.
(function (root) {
  'use strict';

  const VERSIONS = ['0.1', '0.2', '0.3'], CURRENT = '0.3';
  const CORE = {
    relationship_types: ['romantic', 'sexual', 'platonic', 'queerplatonic', 'chosen-family', 'co-parent', 'play-partner', 'friend', 'undefined'],
    group_types: ['house', 'pod', 'polycule', 'family', 'triad', 'quad', 'other'],
  };
  const ENUMS = {
    status: ['active', 'paused', 'ended', 'unknown'],
    style: ['hierarchical', 'non-hierarchical', 'relationship-anarchy'],
    priority: ['anchor', 'primary', 'secondary', 'none'],
    distance: ['nesting', 'local', 'long-distance'],
    contact: ['daily', 'weekly', 'monthly', 'rarely'],
  };
  const RA = 'relationship-anarchy';
  const LOW = '0000-01-01', HIGH = '9999-12-31';
  const ID_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/;
  const DATE_RE = /^\d{4}(-\d{2}(-\d{2})?)?$/;

  const dateKey = (d, dflt) => d ? (d + '-01-01').slice(0, 10) : dflt;
  const covers = (from, to, d) => dateKey(from, LOW) <= d && d < dateKey(to, HIGH);
  const membership = m => typeof m === 'string' ? { person: m } : m;

  function styleOf(doc, pid) {
    const p = doc.people.find(x => x.id === pid) || {};
    return p.style || doc.meta?.style || null;
  }
  const isAnarchic = (doc, r) => r.parties.some(p => styleOf(doc, p.person) === RA);
  const distanceOf = r => r.distance || (r.nesting ? 'nesting' : null);
  // Camera obscura (spec §8): the link shows, nothing about it does.
  const isObscured = (doc, r) => r.parties.some(p => doc.people.find(x => x.id === p.person)?.obscura === true);

  // Upgrade a v0.1/v0.2 document to v0.3 (spec §11): dynamics become tags (switch/fluctuating also set
  // direction "both"), closeness is dropped. Returns a new object; v0.3 documents come back as a copy.
  function upgrade(doc) {
    doc = JSON.parse(JSON.stringify(doc));
    if (!doc || !['0.1', '0.2'].includes(doc.polyml)) return doc;
    doc.polyml = CURRENT;
    if (doc.vocab && typeof doc.vocab === 'object') { delete doc.vocab.dynamics; if (!Object.keys(doc.vocab).length) delete doc.vocab; }
    for (const b of [...(doc.relationships || []), ...(doc.groups || [])]) {
      if (!b || typeof b !== 'object') continue;
      const dyns = [...(b.dynamics || [])];
      for (const h of b.history || []) { if (h && h.dynamics) dyns.push(...h.dynamics); if (h) delete h.dynamics; }
      delete b.dynamics; delete b.closeness;
      if (dyns.length) {
        b.tags = b.tags || [];
        for (const d of dyns) if (!b.tags.includes(d)) b.tags.push(d);
        if (b.parties && dyns.some(d => d === 'switch' || d === 'fluctuating') && !b.direction) b.direction = 'both';
      }
    }
    return doc;
  }

  // A copy where every relationship under camera obscura keeps only its id, parties and status.
  function obscure(doc) {
    const out = JSON.parse(JSON.stringify(doc));
    out.relationships = out.relationships.map(r => isObscured(out, r)
      ? { id: r.id, parties: r.parties.map(p => ({ person: p.person })), types: [], ...(r.status ? { status: r.status } : {}) }
      : r);
    return out;
  }

  function periodAt(bond, d) {
    return (bond.history || []).find(h => covers(h.from, h.to, d)) || null;
  }
  function statusAt(bond, date) {
    if (!date) return bond.status || 'active';
    const d = dateKey(date, '');
    const hist = bond.history || [];
    if (hist.length) {
      const h = periodAt(bond, d);
      if (h) return h.status;
      return dateKey(hist[0].from, LOW) > d ? null : (bond.status || 'active');
    }
    if (bond.since && dateKey(bond.since, LOW) > d) return null;
    return bond.status || 'active';
  }
  function typesAt(bond, date) {
    if (date) { const h = periodAt(bond, dateKey(date, '')); if (h && h.types) return h.types; }
    return bond.types || [];
  }
  function directionAt(rel, date) {
    if (date) { const h = periodAt(rel, dateKey(date, '')); if (h && h.direction) return h.direction; }
    return rel.direction || null;
  }
  function membersAt(group, date) {
    const d = date ? dateKey(date, '') : null;
    return (group.members || []).map(membership)
      .filter(m => d ? covers(m.from, m.to, d) : !m.to)
      .map(m => m.person);
  }

  // Every date mentioned in the document, sorted (for date sliders).
  function allDates(doc) {
    const ds = new Set();
    const add = x => { if (x) ds.add(dateKey(x)); };
    for (const b of [...doc.relationships, ...(doc.groups || [])]) {
      add(b.since);
      for (const h of b.history || []) { add(h.from); add(h.to); }
    }
    for (const g of doc.groups || []) for (const m of (g.members || []).map(membership)) { add(m.from); add(m.to); }
    return [...ds].sort();
  }

  // Validation: structural checks (a subset of the JSON Schema) plus spec §10 rules.
  // v0.1/v0.2 documents are upgraded first. Returns a list of {path, msg}. Empty means valid.
  function validate(doc) {
    const errs = [];
    const err = (path, msg) => errs.push({ path, msg });
    const isObj = x => x && typeof x === 'object' && !Array.isArray(x);
    if (!isObj(doc)) { err('', 'The file is not a JSON object'); return errs; }
    doc = upgrade(doc);
    if (!VERSIONS.includes(doc.polyml)) err('polyml', `Version must be one of ${VERSIONS.join(', ')}`);
    if (!Array.isArray(doc.people)) { err('people', 'people must be a list'); return errs; }
    if (!Array.isArray(doc.relationships)) { err('relationships', 'relationships must be a list'); return errs; }
    const groups = doc.groups || [];
    const vocab = doc.vocab || {};
    const terms = k => new Set([...CORE[k], ...(vocab[k] || []).map(t => t.id)]);
    const rtypes = terms('relationship_types'), gtypes = terms('group_types');
    for (const k of Object.keys(CORE)) for (const t of vocab[k] || []) {
      if (!ID_RE.test(t.id || '')) err(`vocab.${k}`, `Bad term id ${JSON.stringify(t.id)}`);
      if (CORE[k].includes(t.id)) err(`vocab.${k}`, `'${t.id}' repeats a core term`);
    }
    doc.people.forEach((p, i) => { if (p.obscura !== undefined && typeof p.obscura !== 'boolean') err(`people[${i}].obscura`, 'obscura must be true or false'); });
    if (doc.meta?.style && !ENUMS.style.includes(doc.meta.style)) err('meta.style', `Unknown style '${doc.meta.style}'`);

    const checkDate = (path, v) => { if (v !== undefined && !DATE_RE.test(v)) err(path, `'${v}' is not a date (YYYY, YYYY-MM or YYYY-MM-DD)`); };
    const checkEnum = (path, k, v) => { if (v !== undefined && !ENUMS[k].includes(v)) err(path, `'${v}' is not a valid ${k}`); };
    const dupes = (kind, items) => {
      const seen = new Set();
      items.forEach((x, i) => {
        if (!ID_RE.test(x.id || '')) err(`${kind}[${i}].id`, `Bad id ${JSON.stringify(x.id)}: use lowercase letters, digits, - or _`);
        else if (seen.has(x.id)) err(`${kind}[${i}].id`, `Duplicate id '${x.id}'`);
        seen.add(x.id);
      });
    };
    dupes('people', doc.people); dupes('groups', groups); dupes('relationships', doc.relationships);
    const pids = new Set(doc.people.map(p => p.id)), gids = new Set(groups.map(g => g.id));

    doc.people.forEach((p, i) => {
      if (!p.name) err(`people[${i}].name`, `Person '${p.id}' needs a name`);
      checkEnum(`people[${i}].status`, 'status', p.status);
      checkEnum(`people[${i}].style`, 'style', p.style);
    });

    function checkBond(path, label, b) {
      for (const t of b.types || []) if (!rtypes.has(t)) err(`${path}.types`, `${label}: unknown type '${t}'`);
      for (const k of ['dynamics', 'closeness']) if (k in b) err(`${path}.${k}`, `${label}: ${k} was removed in 0.3`);
      checkEnum(`${path}.status`, 'status', b.status);
      checkDate(`${path}.since`, b.since);
      const hist = b.history || [];
      hist.forEach((h, j) => {
        checkEnum(`${path}.history[${j}].status`, 'status', h.status);
        if (!h.status) err(`${path}.history[${j}].status`, `${label}: every history period needs a status`);
        checkDate(`${path}.history[${j}].from`, h.from); checkDate(`${path}.history[${j}].to`, h.to);
        for (const t of h.types || []) if (!rtypes.has(t)) err(`${path}.history[${j}].types`, `${label}: unknown type '${t}' in history`);
      });
      for (let j = 1; j < hist.length; j++)
        if (dateKey(hist[j - 1].to, HIGH) > dateKey(hist[j].from, LOW)) err(`${path}.history`, `${label}: history periods overlap or are out of order`);
      if (hist.length && hist[hist.length - 1].status !== (b.status || 'active')) err(`${path}.status`, `${label}: status does not match the last history period`);
      if (hist.length && b.since && hist[0].from && b.since !== hist[0].from) err(`${path}.since`, `${label}: since differs from the first history period`);
      (b.agreements || []).forEach((a, j) => { if (!a.text) err(`${path}.agreements[${j}]`, `${label}: an agreement needs text`); });
    }

    groups.forEach((g, i) => {
      const path = `groups[${i}]`, label = `Group '${g.id}'`;
      if (!g.name) err(`${path}.name`, `${label} needs a name`);
      if (!gtypes.has(g.type)) err(`${path}.type`, `${label}: unknown group type '${g.type}'`);
      if (g.parent && !gids.has(g.parent)) err(`${path}.parent`, `${label}: unknown parent '${g.parent}'`);
      const seen = new Set();
      (g.members || []).map(membership).forEach((m, j) => {
        if (!pids.has(m.person)) err(`${path}.members[${j}]`, `${label}: unknown member '${m.person}'`);
        if (seen.has(m.person)) err(`${path}.members[${j}]`, `${label}: '${m.person}' is listed more than once`);
        seen.add(m.person);
        checkDate(`${path}.members[${j}].from`, m.from); checkDate(`${path}.members[${j}].to`, m.to);
        if (m.from && m.to && dateKey(m.from) >= dateKey(m.to)) err(`${path}.members[${j}]`, `${label}: membership of '${m.person}' ends before it starts`);
      });
      checkBond(path, label, g);
    });
    const parent = Object.fromEntries(groups.map(g => [g.id, g.parent]));
    for (const id of Object.keys(parent)) {
      const visited = new Set(); let cur = id;
      while (cur && cur in parent) { if (visited.has(cur)) { err('groups', `Group '${id}': parent chain has a cycle`); break; } visited.add(cur); cur = parent[cur]; }
    }

    const pairs = new Map();
    const ended = new Set(doc.people.filter(p => p.status === 'ended').map(p => p.id));
    doc.relationships.forEach((r, i) => {
      const path = `relationships[${i}]`, label = `Relationship '${r.id}'`;
      if (!Array.isArray(r.parties) || r.parties.length !== 2) { err(`${path}.parties`, `${label} needs exactly two people`); return; }
      const [a, b] = r.parties.map(p => p.person);
      for (const p of [a, b]) if (!pids.has(p)) err(`${path}.parties`, `${label}: unknown person '${p}'`);
      if (a === b) err(`${path}.parties`, `${label}: both people are '${a}'`);
      const key = [a, b].sort().join('|');
      if (pairs.has(key)) err(`${path}.parties`, `${label}: same pair as '${pairs.get(key)}'`);
      pairs.set(key, r.id);
      if (!Array.isArray(r.types)) err(`${path}.types`, `${label}: types must be a list`);
      if (pids.has(a) && pids.has(b)) {
        const ra = isAnarchic(doc, r);
        if (ra && r.priority) err(`${path}.priority`, `${label}: priority is not used under relationship anarchy`);
        if (!ra && !isObscured(doc, r) && !(r.types || []).length) err(`${path}.types`, `${label} needs at least one type (only relationship anarchy or camera obscura allows none)`);
      }
      checkEnum(`${path}.priority`, 'priority', r.priority);
      checkEnum(`${path}.distance`, 'distance', r.distance);
      checkEnum(`${path}.contact`, 'contact', r.contact);
      [['', r], ...(r.history || []).map((h, j) => [`.history[${j}]`, h])].forEach(([w, h]) => {
        if (h.direction !== undefined && ![a, b, 'both'].includes(h.direction)) err(`${path}${w}.direction`, `${label}: direction${w ? ' in history' : ''} must be ${a}, ${b} or both, not '${h.direction}'`);
      });
      if (r.nesting && r.distance && r.distance !== 'nesting') err(`${path}.distance`, `${label}: nesting is true but distance is '${r.distance}'`);
      checkBond(path, label, r);
      if ((r.status || 'active') === 'active') for (const p of [a, b]) if (ended.has(p)) err(`${path}.status`, `${label} is active but '${p}' is marked ended`);
    });
    return errs;
  }

  root.PolyML = { VERSIONS, CURRENT, CORE, ENUMS, RA, dateKey, membership, styleOf, isAnarchic, isObscured, distanceOf, upgrade, obscure, statusAt, typesAt, directionAt, membersAt, allDates, validate };
})(typeof window !== 'undefined' ? window : globalThis);
