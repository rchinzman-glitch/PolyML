# polyML specification, v0.2 (draft)

polyML is a plain-text format for describing a relationship network: the people in it, the groups they form, and the relationships between them. A polyML file is the source of truth; tools (the `polyml` library, the 3D viewer, the builder) read it, validate it, and derive views from it.

Machine-readable schema: [`polyml.schema.json`](polyml.schema.json). Example: [`examples/sample.polyml.json`](examples/sample.polyml.json).

## 1. Design goals

1. **Human-editable.** JSON, short ids, sensible defaults.
2. **Open vocabulary.** Relationship types are not a fixed list; documents can add their own terms.
3. **Time-aware.** Relationships, their types and group membership change; history is first-class so tools can show the network at any date.
4. **Graph-native.** People are nodes, relationships are edges, groups are clusters (and can be bonds in their own right). Everything maps directly onto a graph.
5. **Style-neutral.** Hierarchical, non-hierarchical and relationship-anarchist networks are all first-class.

## 2. Document

| Field | Required | Meaning |
|---|---|---|
| `polyml` | yes | Spec version: `"0.2"` (or `"0.1"`, see §10). |
| `meta` | no | `title`, `description`, `updated` date, and `style` (§7), the default for everyone in the document. |
| `vocab` | no | Document-local terms added to the core vocabularies (§6). |
| `people` | yes | List of people (§3). |
| `groups` | no | List of groups (§4). |
| `relationships` | yes | List of relationships (§5). |

Files are JSON and use the extension `.polyml.json`.

### Ids

Every person, group, relationship and vocab term has an `id`: lowercase letters, digits, `_` or `-`, max 64 characters, unique within its list.

### Dates

ISO 8601 with variable precision: `2019`, `2019-06`, or `2019-06-14`. A period runs from `from` (inclusive) to `to` (exclusive); a missing `from` means "since always", a missing `to` means "still ongoing".

### Extensions

Any object that allows it may carry extra fields whose names start with `x-` (e.g. `"x-discord": "ash#1234"`). Tools must preserve them and may ignore them.

## 3. Person

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable id. |
| `name` | yes | Display name. |
| `pronouns` | no | Free text, e.g. `they/them`. |
| `style` | no | `hierarchical`, `non-hierarchical` or `relationship-anarchy`. Overrides `meta.style` for this person (§7). |
| `location` | no | Coarse location, such as a city or region. |
| `tags` | no | Free-form labels. |
| `status` | no | `active` (default), `paused`, `ended`, `unknown`. |
| `notes` | no | Free text. |

## 4. Group

A group is any named set of people: a house, a pod, a polycule, a family, a triad.

| Field | Required | Meaning |
|---|---|---|
| `id`, `name` | yes | |
| `type` | yes | Core: `house`, `pod`, `polycule`, `family`, `triad`, `quad`, `other`; or a `vocab.group_types` id. |
| `parent` | no | Id of an enclosing group. Parent chains must not loop. |
| `members` | no | Each entry is a person id, or `{ person, from?, to?, role? }` for dated membership (someone moving in or out) and roles within the group. |
| `status`, `tags`, `notes` | no | As for people. |
| Bond fields | no | `types`, `dynamics`, `since`, `history`, `agreements`: see §4.1. |

### 4.1 Groups as relationship units

A triad, quad or polycule can relate as one unit, not only as a set of pairings. A group that sets `types` is a **bond** in its own right. It uses the same bond fields as a relationship (`types`, `dynamics`, `since`, `history`, `agreements`), with the same meaning and rules. The pairwise relationships between its members still describe each individual pairing inside it, and none of them is required.

## 5. Relationship

A relationship describes one pairing: it joins exactly two people (an edge). Larger units are groups (§4.1).

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable id. |
| `parties` | yes | Exactly two `{ person, title?, role? }` objects. `title` is what that person is called in this relationship ("big sis"); `role` is their side of an asymmetric dynamic ("dominant"). |
| `types` | yes | Current relationship types (§6). Types stack: `["romantic", "sexual"]`. May be empty only under relationship anarchy (§7). |
| `dynamics` | no | Power or play dynamics (§6). |
| `priority` | no | `anchor`, `primary`, `secondary` or `none`. Not allowed under relationship anarchy. |
| `distance` | no | `nesting` (share a home), `local` or `long-distance`. |
| `nesting` | no | Deprecated in 0.2; `true` means `distance: "nesting"`. |
| `closeness` | no | 1 (distant) to 5 (closest). Tools may use it for layout strength. |
| `contact` | no | How often the two are in touch: `daily`, `weekly`, `monthly`, `rarely`. |
| `status` | no | Current status, default `active`. |
| `since` | no | Start date. Must equal the first history period's `from` when both are given. |
| `history` | no | Ordered periods (§5.1). |
| `agreements` | no | List of `{ text, since?, tags? }`. |
| `tags`, `notes` | no | As for people. |

### 5.1 History

`history` is an ordered list of `{ status, from?, to?, note?, types?, dynamics? }` periods. A period's `types` and `dynamics` give the relationship's types and dynamics during that period; when omitted, the current top-level values apply. This records changes such as a romance that becomes a friendship:

```json
"types": ["friend"],
"history": [
  { "status": "active", "from": "2018", "to": "2020-01", "types": ["sexual"] },
  { "status": "active", "from": "2020-01" }
]
```

The last period's `status` must equal the top-level `status`.

## 6. Vocabularies

Core terms below are always valid. A document adds terms through `vocab.relationship_types`, `vocab.group_types` and `vocab.dynamics`, each a list of `{ id, label?, description?, color? }`. A vocab term must not repeat a core term. Validators reject a term that is neither core nor declared.

- **Relationship types:** `romantic`, `sexual`, `platonic`, `queerplatonic`, `chosen-family`, `co-parent`, `play-partner`, `friend`, `undefined`.
- **Group types:** `house`, `pod`, `polycule`, `family`, `triad`, `quad`, `other`.
- **Dynamics:** `d-s`, `caregiver`, `pet-play`, `age-play`, `switch`, `fluctuating`.

v0.0 (the 2016 PowerShell library) mapped as follows: `rel_type` romantic → `romantic`, dominant/submissive → `dynamics: ["d-s"]` with party `role`, playmate → `play-partner`, fluctuating → `dynamics: ["fluctuating"]`, undefined → `undefined`; `power_dynamic_type` pupplay → `pet-play`, ageplay → `age-play`; `group_type` relationship → a group of type `other`.

## 7. Styles and relationship anarchy

A person's effective style is their own `style`, else `meta.style`. Styles are `hierarchical`, `non-hierarchical` and `relationship-anarchy`.

Relationship anarchy is a first-class style with its own rules. They apply to every relationship where at least one party's effective style is `relationship-anarchy`:

1. `priority` is not allowed.
2. `types` may be empty, or use only custom vocabulary.
3. Tools must not rank types (for example romantic above platonic), and must not weight, sort or size edges by type. They may still use `closeness` and `contact`, which describe the people involved rather than a category.

## 8. Derived data (not stored)

Tools compute these; files must not store them:

- **Metamours:** two people who share a partner but have no relationship of their own.
- **Degree, components, distance** between people.
- **Snapshot at date D:** relationships and groups whose status at D is `active`, with the types, dynamics and members in force at D.

## 9. Validation rules beyond the schema

1. Ids are unique per list; a person appears at most once in a group's `members`.
2. Every referenced person or group id exists.
3. A relationship's two parties are different people, and no two relationships join the same pair.
4. Group `parent` chains have no cycles.
5. Every type, group type and dynamic (including those inside history periods) is core or declared in `vocab`, and no vocab term repeats a core term.
6. History periods are in order and do not overlap; the last period's status equals `status`; `since` equals the first period's `from` when both are set.
7. A membership's `from` is before its `to`.
8. Relationship anarchy rules (§7): no `priority`; `types` may be empty only under relationship anarchy.
9. `nesting: true` conflicts with any `distance` other than `nesting`.
10. A person whose `status` is `ended` has no active relationships.

## 10. Versioning

- The `polyml` field names the spec version a file follows. Tools state which versions they read; the reference tools read `0.1` and `0.2`.
- Minor versions (`0.x`) only add optional fields and core terms, or deprecate fields without removing them, so every valid `0.1` file is a valid `0.2` file.
- A deprecated field (such as `nesting`) keeps working until the next major version, which may remove it.
- The schema's `$id` is <https://rchinzman-glitch.github.io/polyml/spec/polyml.schema.json>.

## 11. Open questions for v0.3

- Directed edges (one-sided crushes, "interested in")?
- Person-level poly orientation (kitchen-table, parallel, solo)?
- Multiple files merged into one network (each person maintains their own slice)?
- Exports to graph formats (GraphML, GEXF, DOT, Mermaid)?
