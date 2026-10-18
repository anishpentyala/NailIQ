import pytest

from ml.eval.eval_end_to_end import metrics


def record(label, verdict, shown=None):
    return {"labels": [label], "findings": {"pitting": {
        "verdict": verdict, "shown": shown or verdict,
    }}}


def test_abstentions_cannot_inflate_detection_or_healthy_accuracy():
    rows = [record("pitting", "outside"), record("pitting", "inconclusive"),
            record("healthy", "within"), record("healthy", "outside"),
            record("healthy", "inconclusive")]
    result = metrics(rows)["pitting"]
    assert result["recall"] == 0.5
    assert result["fp_rate"] == pytest.approx(1 / 3)
    assert result["healthy_correct_rate"] == pytest.approx(1 / 3)
    assert result["balanced_accuracy"] == pytest.approx(5 / 12)


def test_withheld_predictions_do_not_count_as_shown_detections():
    rows = [record("pitting", "outside", "inconclusive")]
    assert metrics(rows)["pitting"]["recall"] == 1
    shown = metrics(rows, lambda r, c: r["findings"][c]["shown"])["pitting"]
    assert shown["recall"] == 0
    assert shown["fp_rate"] is None
    assert shown["balanced_accuracy"] is None


def test_missing_finding_is_a_miss():
    rows = [record("pitting", "outside"), {"labels": ["pitting"], "findings": {}}]
    assert metrics(rows)["pitting"]["recall"] == 0.5


def test_tuner_also_counts_missing_findings_as_misses(monkeypatch):
    from ml.eval import tune_color_decision as tuner
    monkeypatch.setattr(tuner, '_RUN_COVERAGE', frozenset())
    rows = [record('pitting', 'outside'), {'labels': ['pitting'], 'findings': {}},
            {'labels': ['healthy'], 'findings': {}}, record('healthy', 'within')]
    for row in rows:
        row['probs'] = None
    result = tuner.strict(rows, 'pitting')
    assert result['recall'] == 0.5
    assert result['n_pos'] == 2 and result['n_healthy'] == 2
    assert result['abstain_healthy'] == 0.5
