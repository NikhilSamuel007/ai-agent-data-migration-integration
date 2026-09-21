"""Evaluate unchanged autonomy gates against a small labeled smoke set.

Requires real Ollama and MiniLM; exits unsuccessfully on missing models, unsafe
automatic decisions, or no unfamiliar automatic mapping. Not calibration data.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from relay.mapping import map_columns
from relay.profiling import profile_file
from relay.llm import LLM_STATE
from relay.model import MODEL_STATE

def main():
    cases=json.loads((ROOT/'backend/evaluation/mapping_cases.json').read_text())
    results=[]
    for case in cases:
        header=case['header']
        source=dict(name='evaluation.csv',headers=[header],rows=[{header:v} for v in case['values']])
        source['profile']=profile_file(source)
        mapping=map_columns(source)[0]
        automatic=mapping['status']=='automatic'
        safe=not automatic or (not case['review'] and mapping['field']==case['expected'])
        results.append(dict(case=case,mapping=mapping,safe=safe))
        print(header, '->', mapping['field'], mapping['status'], mapping['confidence'], flush=True)
    automatic=[r for r in results if r['mapping']['status']=='automatic']
    semantic=[r for r in automatic if not r['mapping']['evidence']['alias']]
    report=dict(at=datetime.now(timezone.utc).isoformat(),policy='evidence-v3',
        limitation='Small authored regression set, not independent client calibration or an accuracy guarantee.',
        model=MODEL_STATE.copy(),llm=LLM_STATE.copy(),cases=len(results),automatic=len(automatic),
        unfamiliarAutomatic=len(semantic),unsafeAutomatic=sum(not r['safe'] for r in results),
        automaticCoverage=len(automatic)/len(results),results=results)
    (ROOT/'docs/mapping-evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    assert all(r['safe'] for r in results), 'Unsafe automatic mapping; inspect report'
    assert LLM_STATE['status']=='ready' and MODEL_STATE['status']=='ready', 'Real model runtime not ready'
    assert semantic, 'No unfamiliar column was mapped automatically'
    print('Real-model evaluation passed. Report: docs/mapping-evaluation.json')

if __name__=='__main__':
    main()
