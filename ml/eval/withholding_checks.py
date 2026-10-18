"""Paired, displayed-result acceptance; all failures remain in denominators."""
import math

from scripts.report_goal60 import CONDITIONS, healthy_summary, score

PROTECTED = ('cyanosis', 'beaus_lines', 'muehrckes_lines', 'splinter_hemorrhages', 'pitting', 'onychogryphosis')
TARGETS = tuple(c for c in CONDITIONS if c not in ('lindsays_nails', 'onycholysis'))


def shown(record, condition):
    finding = record.get('findings', {}).get(condition, {})
    return finding.get('shown', finding.get('verdict', 'inconclusive'))


def pair(candidate, reference):
    def index(records):
        result = {r['path']: r for r in records}
        if len(result) != len(records):
            raise ValueError('Repeated primary patient/image records')
        return result
    left, right = index(candidate), index(reference)
    if set(left) != set(right) or any(left[p]['labels'] != right[p]['labels'] for p in left):
        raise ValueError('Paired comparison needs identical patients and reviewed labels')
    return [(left[p], right[p]) for p in sorted(left)]


def acceptance(candidate, reference, exact_protected=False):
    pairs = pair(candidate, reference)
    current, baseline = score(candidate, True), score(reference, True)
    scans, old_scans = healthy_summary(candidate, True), healthy_summary(reference, True)
    preserved, coverage = {}, {}
    for condition in PROTECTED:
        row, old = current[condition], baseline[condition]
        preserved[condition] = (row['pos']['outside'] >= old['pos']['outside']
            and row['healthy']['outside'] <= old['healthy']['outside'])
        if exact_protected:
            preserved[condition] &= all(
                (shown(a, condition), a['findings'].get(condition, {}).get('route_id'),
                 a['findings'].get(condition, {}).get('evidence_type')) ==
                (shown(b, condition), b['findings'].get(condition, {}).get('route_id'),
                 b['findings'].get(condition, {}).get('evidence_type')) for a, b in pairs)
    for condition in CONDITIONS:
        row, old = current[condition], baseline[condition]
        coverage[condition] = (row['pos']['inconclusive'] <= old['pos']['inconclusive']
            and row['healthy']['inconclusive'] <= old['healthy']['inconclusive']
            and row['healthy']['within'] >= old['healthy']['within'])
    targets = {c: (current[c]['recall'] is not None and current[c]['recall'] >= .6
                   and current[c]['fp_rate'] is not None and current[c]['fp_rate'] <= .05) for c in TARGETS}
    healthy_pairs = [(a, b) for a, b in pairs if a['labels'] == ['healthy']]
    new_flags = recovered = 0
    for a, b in healthy_pairs:
        new = any(shown(a, c) == 'outside' for c in CONDITIONS)
        old = any(shown(b, c) == 'outside' for c in CONDITIONS)
        new_flags += new and not old
        recovered += old and not new
    n = len(healthy_pairs)
    delta = (new_flags - recovered) / n if n else None
    def interval(count):
        z, p = 2.2414027276, count / n
        denominator = 1 + z * z / n
        center = (p + z * z / (2 * n)) / denominator
        margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
        return max(0, center - margin), min(1, center + margin)
    new_interval, old_interval = (interval(new_flags), interval(recovered)) if n else ((0, 0), (0, 0))
    return {'targets': targets, 'target_count': sum(targets.values()), 'protected': preserved,
        'coverage': coverage, 'healthy_scans_preserved': bool(n) and scans['any_outside'] <= old_scans['any_outside'],
        'candidate': current, 'reference': baseline, 'healthy_scans': scans, 'reference_healthy_scans': old_scans,
        'paired_healthy': {'new_flags': new_flags, 'recovered': recovered, 'rate_difference': delta,
            'approximate_ci95': [new_interval[0] - old_interval[1], new_interval[1] - old_interval[0]] if n else None,
            'interval_method': 'Bonferroni paired-discordance Wilson difference; does not prove population equivalence'},
        'non_regression_passed': bool(n) and scans['any_outside'] <= old_scans['any_outside']
            and all(preserved.values()) and all(coverage.values()),
        'twelve_target_passed': all(targets.values())}


def subgroup_checks(records):
    results = {}
    for field in ('source', 'skin_tone_band'):
        groups = sorted({r.get(field) or 'unknown' for r in records})
        for group in groups:
            subset = [r for r in records if (r.get(field) or 'unknown') == group]
            values = score(subset, True)
            failures = [c for c in TARGETS if values[c]['healthy']['n'] and values[c]['fp_rate'] > .05]
            results[field + ':' + group] = {'metrics': values, 'failures': failures,
                'healthy_n': sum(r['labels'] == ['healthy'] for r in subset)}
    return results
