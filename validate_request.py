#!/usr/bin/env python3
"""Check Seedance 2.0 request bodies against schema/seedance-2.0-request.schema.json before sending them.

    pip install jsonschema
    python validate_request.py body.json [more.json ...]
    echo '{"model": "seedance-2.0-mini", "prompt": "x", "resolution": "1080p"}' | python validate_request.py -

Exit status 0 when every body is valid, 1 otherwise. The server still checks what a schema
cannot: prompt bytes, media length and pixel size, and whether URLs download.
"""
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.exit("pip install jsonschema")

SCHEMA = json.loads((Path(__file__).resolve().parent / "schema" / "seedance-2.0-request.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def _rule(error):
    """The description of the schema rule an error came from: a cross-field rule or the field itself."""
    path = list(error.absolute_schema_path)
    if path[:1] == ["allOf"]:
        return SCHEMA["allOf"][path[1]].get("description", "")
    if path[:1] == ["dependentRequired"]:
        return "end_image needs start_image (end_image_url needs image_url)."
    if path[:1] == ["properties"] and len(path) > 1:
        field = SCHEMA["properties"].get(path[1])
        return field.get("description", "") if isinstance(field, dict) else ""
    return ""


def problems(body):
    """Readable messages for everything wrong with one body; empty when it is valid."""
    found = []
    if isinstance(body, dict):  # fields the schema forbids outright, such as seed
        found += [f"{name}: not supported on Seedance 2.0 (rejected with 400)"
                  for name, rule in SCHEMA["properties"].items() if rule is False and name in body]
    for error in sorted(VALIDATOR.iter_errors(body), key=lambda e: list(e.absolute_path)):
        if error.validator is None:  # a false schema, reported above
            continue
        where = "/".join(str(part) for part in error.absolute_path) or "(body)"
        message = error.message if error.validator not in ("anyOf", "not", "if") else "breaks a rule"
        if error.validator == "additionalProperties":
            message = error.message.replace("Additional properties are not allowed", "unknown field")
        rule = _rule(error)
        found.append(f"{where}: {message}" + (f"  ({rule})" if rule else ""))
    prompt = body.get("prompt") if isinstance(body, dict) else None
    if isinstance(prompt, str) and len(prompt.encode("utf-8")) > 40_000:
        found.append(f"prompt: {len(prompt.encode('utf-8'))} bytes, the limit is 40,000")
    return found


def main(paths):
    failed = False
    for path in paths or ["-"]:
        body = json.load(sys.stdin) if path == "-" else json.loads(Path(path).read_text())
        issues = problems(body)
        failed = failed or bool(issues)
        print(f"{path}: " + ("ok" if not issues else "invalid"))
        for issue in issues:
            print(f"  - {issue}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
