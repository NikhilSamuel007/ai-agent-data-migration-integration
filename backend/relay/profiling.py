"""Deterministic source profiling. No model needed for measurable facts."""
import re
import pandas as pd
from .engine import clean_date, ENUMS

def profile_file(file):
    frame = pd.DataFrame(file['rows'], columns=file['headers']).fillna('')
    columns = []
    for name in file['headers']:
        values = frame[name].astype(str).str.strip()
        present = values[values != '']
        count = len(present)
        ratio = lambda predicate: round(sum(bool(predicate(v)) for v in present) / count, 3) if count else 0.0
        email = ratio(lambda v: re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', v))
        dates = ratio(lambda v: 'value' in clean_date(v) or 'choices' in clean_date(v))
        id_ratio = ratio(lambda v: re.fullmatch(r'[A-Za-z]{0,8}[-_]?\d{1,15}', v))
        numeric = ratio(lambda v: re.fullmatch(r'[+-]?\d+(\.\d+)?', v))
        columns.append(dict(name=name, type='email' if email >= .8 else 'date' if dates >= .8 else 'number' if numeric >= .8 else 'string',
            count=len(values), nonEmpty=count, missing=len(values)-count, unique=int(present.nunique()),
            samples=list(present.drop_duplicates().head(3)), patterns=dict(email=email, date=dates, identifier=id_ratio, text=ratio(lambda v: bool(re.search(r'[A-Za-z]', v))),
                **{field: ratio(lambda v, allowed=allowed: v.lower() in [x.lower() for x in allowed]) for field, allowed in ENUMS.items()})))
    return dict(rowCount=len(frame), columns=columns)
