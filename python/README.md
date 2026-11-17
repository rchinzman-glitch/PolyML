# polyml (Python)

Reference implementation of the polyML v0.1 format (see `../spec/polyml-spec.md`).

```
pip install -e ".[dev]"
polyml validate network.polyml.json
polyml stats network.polyml.json
polyml export --public network.polyml.json -o public.polyml.json
pytest
```
