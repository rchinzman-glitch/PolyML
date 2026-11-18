// Run with: node --test viewer/tests/*.test.js
const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
globalThis.window = globalThis;
require('../polyml.js');
const P = globalThis.PolyML;
const sample = () => JSON.parse(JSON.stringify(require(path.join(__dirname, '../../spec/examples/sample.polyml.json'))));
const rel = (d, id) => d.relationships.find(r => r.id === id);

test('sample is valid', () => assert.deepStrictEqual(P.validate(sample()), []));

const cases = [
  [d => rel(d, 'dee-eli').priority = 'primary', 'relationship anarchy'],
  [d => rel(d, 'ash-cal').types = [], 'at least one type'],
  [d => rel(d, 'ash-bea').history.reverse(), 'overlap'],
  [d => rel(d, 'ash-cal').nesting = true, 'nesting is true'],
  [d => d.groups[2].members.push('bea'), 'more than once'],
  [d => d.vocab.relationship_types.push({ id: 'romantic' }), 'repeats a core term'],
  [d => d.people[0].status = 'ended', 'is marked ended'],
  [d => rel(d, 'ash-bea').closeness = 4, 'removed in 0.3'],
  [d => rel(d, 'bea-dee').direction = 'ash', 'direction must be'],
  [d => rel(d, 'cal-fox').history[0].direction = 'x', 'direction in history'],
  [d => d.people[6].obscura = 'yes', 'obscura must be'],
];
for (const [mutate, expected] of cases) {
  test(`rejects: ${expected}`, () => {
    const d = sample(); mutate(d);
    const msgs = P.validate(d).map(e => e.msg);
    assert.ok(msgs.some(m => m.includes(expected)), msgs.join('\n'));
  });
}

test('types and membership over time', () => {
  const d = sample();
  assert.deepStrictEqual(P.typesAt(rel(d, 'cal-fox'), '2019'), ['sexual']);
  assert.deepStrictEqual(P.typesAt(rel(d, 'cal-fox')), ['friend']);
  const house = d.groups.find(g => g.id === 'maple-house');
  assert.ok(P.membersAt(house, '2021').includes('cal'));
  assert.ok(!P.membersAt(house).includes('cal'));
});

test('upgrade from 0.2 moves dynamics to tags and drops closeness', () => {
  const v02 = { polyml: '0.2', vocab: { dynamics: [{ id: 'brat' }] }, people: [{ id: 'a', name: 'A' }, { id: 'b', name: 'B' }],
    relationships: [{ id: 'ab', parties: [{ person: 'a' }, { person: 'b' }], types: ['romantic'], dynamics: ['d-s', 'switch'],
      closeness: 4, tags: ['d-s'], history: [{ status: 'active', dynamics: ['brat'] }] }] };
  assert.deepStrictEqual(P.validate(v02), []);
  const up = P.upgrade(v02), r = up.relationships[0];
  assert.strictEqual(up.polyml, '0.3');
  assert.ok(!('vocab' in up) && !('closeness' in r) && !('dynamics' in r) && !('dynamics' in r.history[0]));
  assert.deepStrictEqual(r.tags, ['d-s', 'switch', 'brat']);
  assert.strictEqual(r.direction, 'both');
  assert.strictEqual(v02.relationships[0].closeness, 4);
});

test('direction and camera obscura', () => {
  const d = sample();
  assert.strictEqual(P.directionAt(rel(d, 'bea-dee')), 'bea');
  assert.strictEqual(P.directionAt(rel(d, 'ash-bea')), null);
  assert.ok(P.isObscured(d, rel(d, 'dee-gus')) && !P.isObscured(d, rel(d, 'bea-dee')));
  rel(d, 'dee-gus').types = [];
  assert.deepStrictEqual(P.validate(d), []);
  assert.deepStrictEqual(rel(P.obscure(d), 'dee-gus'), { id: 'dee-gus', parties: [{ person: 'dee' }, { person: 'gus' }], types: [] });
});
