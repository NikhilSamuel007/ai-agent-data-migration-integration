import io
from datetime import datetime
import pytest
from openpyxl import Workbook
from relay.engine import clean_date, clean, reconcile, validate
from relay.ingest import ingest
from relay.mapping import map_columns
from relay.profiling import profile_file

def test_dates():
    assert clean_date('21/05/2024')['value'] == '2024-05-21'
    assert clean_date('05/21/2024')['value'] == '2024-05-21'
    assert clean_date('03/04/2024')['choices'] == ['2024-04-03', '2024-03-04']
    assert clean_date('2024-02-29')['value'] == '2024-02-29'
    assert clean_date('March 12 1990')['value'] == '1990-03-12'
    assert clean_date('12 March 1990')['value'] == '1990-03-12'
    for value in ['2023-02-29', '2024-13-10', 'March 4', '00/04/2024']:
        assert 'error' in clean_date(value)
        assert 'choices' not in clean_date(value)

def test_cleanup():
    source = ingest('test.csv', b'Employee ID,First Name,Last Name,Work Email,Date of Birth,Employment Status\nE1,Ada,Lovelace,ada@example.com,1990-01-13,Active')
    source['profile'] = profile_file(source)
    mapping = map_columns(source)
    assert all(m['status'] == 'automatic' for m in mapping)
    result = clean({'Employee ID': 'E1', 'First Name': '  Ada ', 'Last Name': 'Lovelace', 'Work Email': ' ADA@EXAMPLE.COM ', 'Date of Birth': '13/01/1990', 'Employment Status': 'Active'}, mapping)
    assert result['record']['first_name'] == 'Ada'
    assert result['record']['email'] == 'ada@example.com'
    assert result['record']['date_of_birth'] == '1990-01-13'
    assert len(result['changes']) == 3
    assert not result['errors']

def test_required_values():
    assert len(validate({})) == 6
    assert len(validate(dict(employee_id='1',first_name='A',last_name='B',email='bad',date_of_birth='03/04/1990',employment_status='Active'))) == 2

def test_duplicates_and_conflicts():
    data = dict(employee_id='1', first_name='Ada', last_name='Lovelace', email='a@example.com', department='R&D', date_of_birth='1990-01-01', employment_status='Active', account_status='')
    def row(id, **changes):
        return dict(id=id, data=dict(data, **changes), errors=[], status='ready')
    result = reconcile([row('a'), row('b')])
    assert result[1]['status'] == 'duplicate'
    assert result[1]['duplicateOf'] == 'a'
    assert all(r['status'] == 'review' for r in reconcile([row('a'), row('b', department='Finance')]))
    assert all(r['status'] == 'review' for r in reconcile([row('a'), row('b', email='other@example.com')]))

def test_csv():
    assert ingest('test.csv', b'name,email\n"Last, First",a@example.com')['rows'][0]['name'] == 'Last, First'
    with pytest.raises(ValueError, match='unique'):
        ingest('bad.csv', b'name,name\na,b')
    with pytest.raises(ValueError, match='same number'):
        ingest('bad.csv', b'name,email\na,b,c')

def test_excel():
    book = Workbook()
    book.active.append(['Employee Name', 'Start Date'])
    book.active.append(['Ada', datetime(2024, 1, 13)])
    buffer = io.BytesIO()
    book.save(buffer)
    assert ingest('people.xlsx', buffer.getvalue())['rows'][0]['Start Date'] == '2024-01-13'
    book.active['B2'] = '=TODAY()'
    buffer = io.BytesIO()
    book.save(buffer)
    with pytest.raises(ValueError, match='formulas'):
        ingest('formula.xlsx', buffer.getvalue())

def test_model_failure_requires_review(monkeypatch):
    monkeypatch.setattr('relay.mapping.suggest', lambda *args: [])
    monkeypatch.setattr('relay.mapping.propose', lambda *args: None)
    file=ingest('test.csv', b'Contact,Email,Work Email\na@example.com,a@example.com,b@example.com')
    file['profile']=profile_file(file)
    mapping=map_columns(file)
    assert all(m['status']=='pending' for m in mapping)

def test_status_and_birth_date_are_validated_without_guessing():
    data = dict(employee_id='E1', first_name='Ada', last_name='Lovelace', email='a@example.com', date_of_birth='2990-01-01', employment_status='Unknown', account_status='Leave')
    assert {e['field'] for e in validate(data)} == {'date_of_birth', 'employment_status', 'account_status'}
    result = clean(dict(data, date_of_birth='1990-01-01', employment_status=' active ', account_status='LOCKED'), [dict(header=f,field=f) for f in data])
    assert result['record']['employment_status'] == 'Active'
    assert result['record']['account_status'] == 'Locked'
    assert not result['errors']
