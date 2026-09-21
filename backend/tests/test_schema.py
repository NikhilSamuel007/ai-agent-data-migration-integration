"""Guard against drift between schema, cleanup, and API/model contracts."""
import json
from pathlib import Path
from relay.engine import FIELDS, ENUMS
from relay.contracts import TargetRecord, MappingDecision
from relay.llm import MappingProposal

def test_schema_matches_runtime_contracts():
    schema=json.loads((Path(__file__).resolve().parents[1]/'schema.json').read_text())['fields']
    assert set(schema)==set(FIELDS)==set(TargetRecord.model_fields)
    assert set(MappingProposal.model_json_schema()['properties']['target_field']['enum'])==set(schema)
    assert set(MappingDecision.model_json_schema()['properties']['field']['anyOf'][0]['enum'])==set(schema)
    for field,values in ENUMS.items():
        assert schema[field]['enum']==list(values)
