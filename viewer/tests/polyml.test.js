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
  [d => rel(d, 'ash-bea').closeness = 9, 'closeness'],
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
