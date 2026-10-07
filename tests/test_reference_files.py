"""The schema, the OpenAPI file and the examples agree with each other and with the documented rules."""
import json
import sys
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import validate_request  # noqa: E402

SCHEMA = json.loads((ROOT / "schema" / "seedance-2.0-request.schema.json").read_text())
OPENAPI = yaml.safe_load((ROOT / "openapi.yaml").read_text())
URL = {"url": "https://example.com/a.png"}


def body(**fields):
    return {"model": "seedance-2.0", "prompt": "a lighthouse in fog", **fields}


def test_schema_is_valid_draft_2020_12():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("path", sorted((ROOT / "examples" / "requests").glob("*.json")), ids=lambda p: p.name)
def test_every_example_request_is_valid(path):
    assert validate_request.problems(json.loads(path.read_text())) == []


@pytest.mark.parametrize("fields", [
    {"model": "seedance-2.0-mini", "resolution": "1080p"},
    {"model": "seedance-2.0-fast", "resolution": "4k"},
    {"aspect_ratio": "adaptive"},
    {"reference_audios": [URL]},
    {"start_image": URL, "reference_images": [URL]},
    {"image_url": "https://example.com/a.png", "image_urls": ["https://example.com/b.png"]},
    {"end_image": URL},
    {"seed": 42},
    {"n": 2},
    {"watermark": True},
    {"duration": 16},
    {"duration": 3},
    {"duration": 5, "seconds": 5},
    {"reference_images": [URL] * 10},
    {"reference_videos": [URL] * 4},
    {"start_image": {"url": "http://example.com/a.png"}},
    {"prompt": "   "},
    {"model": "seedance-2.5"},
    {"camera_fixed": True},
], ids=lambda f: ",".join(f))
def test_documented_mistakes_are_rejected(fields):
    assert validate_request.problems(body(**fields)), fields


def test_prompt_byte_limit_is_checked_beside_the_schema():
    assert validate_request.problems(body(prompt="界" * 13_334))  # 40,002 bytes
    assert validate_request.problems(body(prompt="界" * 13_333)) == []  # 39,999 bytes


@pytest.mark.parametrize("name", ["job_pending.json", "job_done.json", "job_failed.json"])
def test_example_jobs_match_the_openapi_job_schema(name):
    validator = jsonschema.Draft202012Validator({**OPENAPI, "$ref": "#/components/schemas/Job"})
    validator.validate(json.loads((ROOT / "examples" / "responses" / name).read_text()))


def test_example_error_and_ticket_match_their_schemas():
    for ref, name in (("ErrorBody", "error_400.json"), ("UploadTicket", "upload_ticket.json")):
        validator = jsonschema.Draft202012Validator({**OPENAPI, "$ref": f"#/components/schemas/{ref}"})
        validator.validate(json.loads((ROOT / "examples" / "responses" / name).read_text()))


def test_openapi_document_is_valid():
    validator = pytest.importorskip("openapi_spec_validator")
    readers = pytest.importorskip("openapi_spec_validator.readers")
    spec, base_uri = readers.read_from_filename(str(ROOT / "openapi.yaml"))
    validator.validate(spec, base_uri=base_uri)


def test_cli_exit_codes(tmp_path, capsys):
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps(body(duration=6)))
    bad.write_text(json.dumps(body(model="seedance-2.0-mini", resolution="4k")))
    assert validate_request.main([str(good)]) == 0
    assert validate_request.main([str(bad)]) == 1
    assert "resolution" in capsys.readouterr().out
