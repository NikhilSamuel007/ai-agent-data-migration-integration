"""Deterministic policy: uncertain values never acquire write authority."""
import re
from datetime import date, datetime

FIELDS = ['employee_id', 'first_name', 'last_name', 'email', 'date_of_birth', 'department', 'employment_status', 'account_status']
ALIASES = {
    'employee_id': ['employee id', 'employee number', 'staff id', 'emp id'],
    'first_name': ['first name', 'fname', 'givenname', 'given name'],
    'last_name': ['last name', 'lname', 'surname', 'family name'],
    'email': ['email', 'work email', 'email address', 'emailaddress', 'employee email'],
    'department': ['department', 'team', 'division', 'dept'],
    'date_of_birth': ['date of birth', 'dob', 'birthdate', 'birth date'],
    'employment_status': ['employment status', 'employmentstatus'],
    'account_status': ['account status', 'accountstatus', 'login status'],
}
ENUMS = {'employment_status': ('Active', 'Inactive', 'Leave'),
         'account_status': ('Active', 'Inactive', 'Locked')}

def clean_date(value):
    s = str(value or '').strip()
    if re.fullmatch(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', s):
        y, m, d = map(int, re.split(r'[-/]', s))
    elif re.fullmatch(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', s):
        a, b, y = map(int, re.split(r'[-/]', s))
        if 1 <= a <= 12 and 1 <= b <= 12 and a != b and y >= 1:
            return {'error': 'Ambiguous date: day/month and month/day are both valid',
                    'choices': [f'{y:04d}-{b:02d}-{a:02d}', f'{y:04d}-{a:02d}-{b:02d}']}
        d, m = (a, b) if a > 12 else (b, a)
    else:
        # Explicit English month names have no day/month ordering ambiguity.
        if re.fullmatch(r'(?:[A-Za-z]+ \d{1,2},? \d{4}|\d{1,2} [A-Za-z]+ \d{4})', s):
            for pattern in ('%B %d %Y', '%b %d %Y', '%d %B %Y', '%d %b %Y'):
                try:
                    return {'value': datetime.strptime(s.replace(',', ''), pattern).date().isoformat()}
                except ValueError:
                    pass
        return {'error': 'Date must be a real calendar date in YYYY-MM-DD format'}
    try:
        return {'value': date(y, m, d).isoformat()}
    except ValueError:
        return {'error': 'Invalid calendar date'}

def validate(record):
    errors = []
    for field in FIELDS:
        if field in record and not isinstance(record[field], str):
            errors.append(dict(field=field, reason='Value must be text'))
    if errors:
        return errors
    for field in ('employee_id', 'first_name', 'last_name', 'email', 'date_of_birth', 'employment_status'):
        if not record.get(field):
            errors.append(dict(field=field, reason='Required value is missing'))
    for field in ('email',):
        if record.get(field) and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', record[field]):
            errors.append(dict(field=field, reason='Invalid email address'))
    if record.get('date_of_birth'):
        result = clean_date(record['date_of_birth'])
        if 'error' in result:
            error = dict(field='date_of_birth', reason=result['error'])
            if 'choices' in result:
                error['choices'] = result['choices']
            errors.append(error)
        elif date.fromisoformat(result['value']) > date.today():
            errors.append(dict(field='date_of_birth', reason='Date of birth cannot be in the future'))
    for field, allowed in ENUMS.items():
        if record.get(field) and record[field] not in allowed:
            errors.append(dict(field=field, reason='Allowed values: ' + ', '.join(allowed)))
    return errors

def clean(raw, mapping):
    record, changes = dict.fromkeys(FIELDS, ''), []
    for item in mapping:
        field = item['field']
        if not field:
            continue
        original = str(raw.get(item['header']) or '')
        value = re.sub(r'\s+', ' ', original.strip())
        if 'email' in field:
            value = value.lower()
        if field == 'date_of_birth':
            value = clean_date(value).get('value', value)
        if field in ENUMS:
            value = next((v for v in ENUMS[field] if v.lower() == value.lower()), value)
        record[field] = value
        if value != original:
            changes.append(dict(field=field, before=original, after=value,
                                reason='Whitespace, email or known status casing, or unambiguous date normalization'))
    return dict(record=record, changes=changes, errors=validate(record))

def reconcile(records):
    seen, ids = {}, {}
    def conflict(rows, reason):
        for row in rows:
            row['status'] = 'review'
            if not any(e['field'] == 'identity' and e['reason'] == reason for e in row['errors']):
                row['errors'].append(dict(field='identity', reason=reason))
    for row in records:
        if row['status'] == 'rejected' or not row['data'].get('email'):
            continue
        key = row['data']['email']
        previous = seen.get(key)
        if previous is None:
            seen[key] = row
        elif all(row['data'].get(f) == previous['data'].get(f) for f in FIELDS):
            row.update(status='duplicate', duplicateOf=previous['id'])
        else:
            conflict([row, previous], 'Same email has conflicting records. Correct the identity or reject one record; never silently overwrite.')
    for row in records:
        if row['status'] in ('rejected', 'duplicate') or not row['data'].get('employee_id'):
            continue
        key = row['data']['employee_id']
        previous = ids.get(key)
        if previous and previous['data']['email'] != row['data']['email']:
            conflict([previous, row], 'Same employee ID has different email addresses. Correct or reject the conflicting record.')
        else:
            ids[key] = row
    return records
