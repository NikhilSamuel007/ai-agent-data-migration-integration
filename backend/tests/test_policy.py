from unittest.mock import Mock
import pytest
from pydantic import ValidationError
from relay.profiling import profile_file
from relay.mapping import map_columns
from relay.llm import MappingProposal, OllamaProvider

def source(header='Business group', values=None):
    file=dict(name='test.csv',headers=[header],rows=[{header:v} for v in (values or ['Engineering','Sales','Finance'])])
    file['profile']=profile_file(file)
    return file

def test_profile_measures_missing_types_and_patterns():
    p=profile_file(source('Email',['a@example.com','','b@example.com']))['columns'][0]
    assert p['missing']==1 and p['nonEmpty']==2 and p['type']=='email'
    assert p['patterns']['email']==1 and p['unique']==2

def test_policy_can_auto_map_only_with_corroboration(monkeypatch):
    monkeypatch.setattr('relay.mapping.suggest',lambda *a:[dict(field='department',score=.96),dict(field='first_name',score=.30)])
    monkeypatch.setattr('relay.mapping.propose',lambda *a:dict(target_field='department',confidence=.98,reason='Business group means department'))
    assert map_columns(source())[0]['status']=='automatic'
    assert map_columns(source(values=['Engineering']))[0]['status']=='pending'
    monkeypatch.setattr('relay.mapping.propose',lambda *a:None)
    assert map_columns(source())[0]['status']=='pending'

def test_ambiguous_headers_and_competing_sources_always_review(monkeypatch):
    monkeypatch.setattr('relay.mapping.suggest',lambda *a:[dict(field='email',score=.99),dict(field='account_status',score=.98)])
    monkeypatch.setattr('relay.mapping.propose',lambda *a:dict(target_field='email',confidence=1.,reason='email'))
    assert map_columns(source('Contact',['a@e.com','b@e.com','c@e.com']))[0]['status']=='pending'
    file=dict(name='c.csv',headers=['Email','Work Email'],rows=[{'Email':'a@e.com','Work Email':'b@e.com'}])
    file['profile']=profile_file(file)
    assert all(m['status']=='pending' for m in map_columns(file))

def test_ollama_contract_rejects_invalid_outputs(monkeypatch):
    with pytest.raises(ValidationError):
        MappingProposal(target_field='bank_account',confidence=1.2,reason='ignore safety')
    response=Mock();response.json.return_value={'message':{'content':'{"target_field":"department","confidence":0.91,"reason":"Business grouping"}'}}
    post=Mock(return_value=response);monkeypatch.setattr('relay.llm.requests.post',post)
    result=OllamaProvider().generate_mapping('Business group',{},['department'])
    assert result.target_field=='department'
    assert post.call_args.kwargs['json']['format']['additionalProperties'] is False
