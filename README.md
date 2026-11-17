# polyML

polyML is an open format for describing relationship networks: the people in them, the groups they form (houses, pods, polycules, families), and the relationships between them. It also covers how those relationships change over time.

- **Spec:** [`spec/polyml-spec.md`](spec/polyml-spec.md), v0.2 draft (reads v0.1 files too), with a JSON Schema at [`spec/polyml.schema.json`](spec/polyml.schema.json)
- **3D viewer:** [`viewer/`](viewer/), a static web page built on [3d-force-graph](https://github.com/vasturiano/3d-force-graph). It's published to GitHub Pages.
- **Python library and CLI:** [`python/`](python/) provides `polyml validate` and `polyml stats`.
- **Legacy:** [`legacy/powershell/`](legacy/powershell/) holds the original 2016 PowerShell class library (spec v0.0). Spec §6 shows how it maps to the current spec.

![viewer screenshot](docs/viewer-screenshot.png)

## Quick start

```sh
cd python
pip install -e ".[dev]"
polyml validate ../spec/examples/sample.polyml.json
pytest
```

To view your own network, open the viewer and use **Open file…** or drag a `.polyml.json` file onto the graph.

## License

- **Spec, schema and examples** (`spec/`): [CC BY-SA 4.0](spec/LICENSE). You can share and adapt the spec if you credit polyML and release your changes under the same license.
- **Code** (viewer, Python library, CI): [GPL-3.0-or-later](LICENSE).
