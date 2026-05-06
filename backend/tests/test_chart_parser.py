from pathlib import Path

import pytest

from app.extraction.chart_parser import parse_bundle, parse_bundle_file
from app.schemas.patient import Patient

DATA = Path(__file__).resolve().parents[2] / "data" / "patients" / "sample_back_pain.json"


def test_parse_bundle_smoke() -> None:
    p = parse_bundle_file(DATA)
    assert isinstance(p, Patient)
    assert p.age == 54
    assert p.sex == "F"
    assert len(p.evidence) == 6
    types = {e.type for e in p.evidence}
    assert types == {"diagnosis", "procedure", "medication", "lab", "imaging"}


def test_spans_match_raw_chart() -> None:
    p = parse_bundle_file(DATA)
    for ev in p.evidence:
        s, x = ev.char_span
        assert p.raw_chart[s:x] == ev.source_text, ev.id


def test_medication_uses_medication_codeable_concept() -> None:
    p = parse_bundle_file(DATA)
    meds = [e for e in p.evidence if e.type == "medication"]
    assert len(meds) == 1
    assert meds[0].code == "5640"
    assert "Ibuprofen" in meds[0].description


def test_bundle_without_patient_raises() -> None:
    with pytest.raises(ValueError, match="Patient"):
        parse_bundle({"resourceType": "Bundle", "entry": []})


def test_non_bundle_raises() -> None:
    with pytest.raises(ValueError, match="Bundle"):
        parse_bundle({"resourceType": "Patient"})
