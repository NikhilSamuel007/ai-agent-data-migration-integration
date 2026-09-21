"""Combine corroborating evidence; confidence here is an uncalibrated policy score."""
import re
from .engine import FIELDS, ALIASES, ENUMS
from .model import suggest
from .llm import propose, LLM_STATE

def compatibility(field, profile):
    patterns = profile.get('patterns', {})
    if field in ('email',):
        value = patterns.get('email', 0)
    elif field == 'date_of_birth':
        value = patterns.get('date', 0)
    elif field == 'employee_id':
        value = patterns.get('identifier', 0)
    elif field in ENUMS:
        value = patterns.get(field, 0)
    else:
        value = patterns.get('text', 0)
    return value

def map_columns(file):
    profiles = {p['name']: p for p in file['profile']['columns']}
    normalized = {h: re.sub(r'\s+', ' ', re.sub(r'[_-]', ' ', h.lower())).strip() for h in file['headers']}
    explicit = {h: next((f for f in FIELDS if normalized[h] in ALIASES[f]), None) for h in file['headers']}
    reserved = {f for f in explicit.values() if f}
    result = []
    for header in file['headers']:
        field, profile = explicit[header], profiles[header]
        unique_alias = field and list(explicit.values()).count(field) == 1
        if unique_alias:
            result.append(dict(header=header, field=field, proposedField=field, status='automatic', confidence=1.0,
                reason='Unique explicit alias. Values are independently validated after normalization.', suggestions=[],
                evidence=dict(alias=True, patternCompatibility=compatibility(field, profile), policy='alias-v3')))
            continue
        candidates = suggest(header, FIELDS)
        proposal = propose(header, profile, FIELDS)
        winner = candidates[0]['field'] if candidates else (proposal['target_field'] if proposal else None)
        semantic = max(0, candidates[0]['score']) if candidates else 0
        margin = semantic - max(0, candidates[1]['score']) if len(candidates) > 1 else 0
        compatible = compatibility(winner, profile) if winner else 0
        agrees = bool(proposal and proposal['target_field'] == winner)
        llm_score = proposal['confidence'] if agrees else 0
        score = round(.65 * semantic + .15 * llm_score + .20 * compatible, 3)
        ambiguous = normalized[header] in ('contact', 'status', 'date', 'id', 'person', 'owner')
        auto = bool(winner and winner not in reserved and score >= .90 and semantic >= .80 and margin >= .20
                    and compatible >= .95 and agrees and llm_score >= .90 and not ambiguous and profile['nonEmpty'] >= 3)
        reason = ('Corroborating model and value evidence meet all policy gates.' if auto else
                  'Review required: ambiguous header, weak or conflicting evidence, competing target, or insufficient samples.')
        if normalized[header] == 'status':
            reason = 'Status may describe HR employment or platform account access. Active and Inactive occur in both; confirm the source meaning.'
        result.append(dict(header=header, field=winner if auto else None, proposedField=winner, status='automatic' if auto else 'pending',
            confidence=score, reason=reason, suggestions=candidates, llmProposal=proposal,
            evidence=dict(alias=False, semanticSimilarity=round(semantic, 3), topTwoMargin=round(margin, 3),
                llmAgreement=agrees, llmConfidence=llm_score, valueCompatibility=compatible,
                samples=profile['nonEmpty'], ambiguousHeader=ambiguous, policy='evidence-v3',
                providerStatus=LLM_STATE['status'], providerError=LLM_STATE['error'])))
        if auto:
            reserved.add(winner)
    # Two semantic proposals for one field must both be reviewed, not ordered into authority.
    for item in result:
        conflicts = [m for m in result if m.get('proposedField') == item.get('proposedField') and m.get('proposedField')]
        if len(conflicts) > 1 and not item['evidence']['alias']:
            item.update(field=None, status='pending', reason='Multiple source columns compete for this target field.')
    return result
