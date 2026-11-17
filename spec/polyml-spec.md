# polyML specification, v0.1 (draft)

polyML is a plain-text format for describing a relationship network: the people in it, the groups they form, and the relationships between pairs of them. A polyML file is the source of truth; tools (the `polyml` library, the 3D viewer) read it, validate it, and derive views from it.

Machine-readable schema: [`polyml.schema.json`](polyml.schema.json). Example: [`examples/sample.polyml.json`](examples/sample.polyml.json).

## 1. Design goals

1. **Human-editable.** JSON, short ids, sensible defaults.
2. **Open vocabulary.** Relationship types are not a fixed list; documents can add their own terms.
3. **Time-aware.** Relationships change; history is first-class so tools can show the network at any date.
4. **Graph-native.** People are nodes, relationships are edges, groups are clusters. Everything maps directly onto a graph.

## 2. Document

| Field | Required | Meaning |
|---|---|---|
| `polyml` | yes | Spec version, `"0.1"`. |
| `meta` | no | Title, description, `updated` date. |
| `vocab` | no | Document-local terms added to the core vocabularies (§6). |
| `people` | yes | List of people (§3). |
| `groups` | no | List of groups (§4). |
| `relationships` | yes | List of relationships (§5). |

Files are JSON and use the extension `.polyml.json`.

### Ids

Every person, group, relationship and vocab term has an `id`: lowercase letters, digits, `_` or `-`, max 64 characters, unique within its list. 

### Dates

ISO 8601 with variable precision: `2019`, `2019-06`, or `2019-06-14`.

### Extensions

Any object that allows it may carry extra fields whose names start with `x-` (e.g. `"x-discord": "ash#1234"`). Tools must preserve them and may ignore them.

## 3. Person

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable id. |
| `name` | yes | Display name or pseudonym. |
| `pronouns` | no | Free text, e.g. `they/them`. |
| `tags` | no | Free-form labels. |
| `status` | no | `active` (default), `paused`, `ended`, `unknown`. |
| `notes` | no | Free text. |

## 4. Group

A group is any named set of people: a house, a pod, a polycule, a family.

| Field | Required | Meaning |
|---|---|---|
| `id`, `name` | yes | |
| `type` | yes | Core: `house`, `pod`, `polycule`, `family`, `other`; or a `vocab.group_types` id. |
| `parent` | no | Id of an enclosing group. Parent chains must not loop. |
| `members` | no | Person ids. |
| `status`, `tags` | no | As for people. |

Triads and larger units are modelled as a group plus the pairwise relationships inside it.

## 5. Relationship

A relationship always joins exactly two people (an edge).

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable id. |
| `parties` | yes | Exactly two `{ person, title?, role? }` objects. `title` is what that person is called in this relationship ("big sis"); `role` is their side of an asymmetric dynamic ("dominant"). |
| `types` | yes | One or more relationship types (§6). Types stack: `["romantic", "sexual"]`. |
| `dynamics` | no | Power or play dynamics (§6). |
| `nesting` | no | `true` if the two share a home. |
| `status` | no | Current status, default `active`. |
| `since` | no | Start date. |
| `history` | no | Ordered list of `{ status, from?, to?, note? }` periods. When present, the last period's status should equal `status`. |
| `tags`, `notes` | no | As for people. |

## 6. Vocabularies

Core terms below are always valid. A document adds terms through `vocab.relationship_types`, `vocab.group_types` and `vocab.dynamics`, each a list of `{ id, label?, description?, color? }`. Validators reject a term that is neither core nor declared.

- **Relationship types:** `romantic`, `sexual`, `platonic`, `queerplatonic`, `chosen-family`, `co-parent`, `play-partner`, `friend`, `undefined`.
- **Group types:** `house`, `pod`, `polycule`, `family`, `other`.
- **Dynamics:** `d-s`, `caregiver`, `pet-play`, `age-play`, `switch`, `fluctuating`.

v0.0 (the 2016 PowerShell library) mapped as follows: `rel_type` romantic → `romantic`, dominant/submissive → `dynamics: ["d-s"]` with party `role`, playmate → `play-partner`, fluctuating → `dynamics: ["fluctuating"]`, undefined → `undefined`; `power_dynamic_type` pupplay → `pet-play`, ageplay → `age-play`; `group_type` relationship → a group of type `other`.

## 7. Derived data (not stored)

Tools compute these; files must not store them:

- **Metamours:** two people who share a partner but have no relationship of their own.
- **Degree, components, distance** between people.
- **Snapshot at date D:** the relationships whose history has an `active` period covering D.

## 8. Validation rules beyond the schema

1. Ids are unique per list.
2. Every referenced person or group id exists.
3. A relationship's two parties are different people, and no two relationships join the same pair.
4. Group `parent` chains have no cycles.
5. Every type, group type and dynamic is core or declared in `vocab`.
6. History periods are in order and do not overlap.

## 9. Open questions for v0.2

- Directed edges (one-sided crushes, "interested in")?
- Agreements and boundaries as structured data?
- Multiple files merged into one network (each person maintains their own slice)?
