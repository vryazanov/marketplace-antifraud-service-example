import math
from dataclasses import replace

import pytest

from src.domain.entities import Category, Policy, Signals


def test_policy_collects_every_reason_and_keeps_fraud_distinct():
    signals = Signals(
        {c: 0.9 if c != Category.FRAUD else 0.1 for c in Category}, "test", {}
    )
    decision = Policy().decide(signals)
    assert decision.blocked and decision.reason
    assert Category.FRAUD not in decision.categories
    assert len(decision.categories) == 4
    assert "угрозы" in decision.reason


def test_approval_has_no_reason():
    decision = Policy().decide(Signals({c: 0.1 for c in Category}, "test", {}))
    assert not decision.blocked and decision.reason is None


@pytest.mark.parametrize("value", [math.nan, math.inf, -0.1, 1.1, True])
def test_invalid_signals_are_rejected(value):
    scores = {c: 0.1 for c in Category}
    scores[Category.FRAUD] = value
    with pytest.raises(ValueError):
        Signals(scores, "test", {})


def test_threshold_is_inclusive():
    scores = {c: 0.1 for c in Category}
    scores[Category.FRAUD] = 0.85
    assert Policy().decide(Signals(scores, "test", {})).blocked


def test_fingerprint_tracks_content_not_identity(snapshot):
    assert snapshot.fingerprint() == replace(snapshot, ad_id=22).fingerprint()
    assert snapshot.fingerprint() != replace(snapshot, price=500).fingerprint()
