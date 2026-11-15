import argparse
import hashlib
import json

import pytest

from bin import evaluate
from src.application.ports.classifier import ClassifierUnavailable
from src.domain.entities import Category, Signals


def experiment(tmp_path):
    dataset = tmp_path / "dataset.jsonl"
    rows = [
        {
            "id": str(i),
            "split": "train",
            "ad": {
                "title": "Тест",
                "description": "Тестовый текст",
                "price": 1,
                "category": "test",
                "city": "Москва",
            },
            "expected": {"blocked": False, "categories": []},
        }
        for i in range(2)
    ]
    dataset.write_text("\n".join(json.dumps(row) for row in rows))
    return argparse.Namespace(
        dataset=dataset, output=tmp_path / "result.json", split="train"
    )


async def test_experiment_records_model_and_comparable_metrics_without_secrets(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("LMS_LLM_API_KEY", "private-test-key")
    calls = []

    class Classifier:
        def __init__(self, client):
            pass

        async def classify(self, snapshot):
            calls.append(snapshot)
            return Signals(
                {c: 0.1 for c in Category},
                "test-model",
                {"requests_charged": 5, "remaining_requests": 10},
            )

    monkeypatch.setattr(evaluate, "JevClassifier", Classifier)
    args = experiment(tmp_path)
    await evaluate.evaluate(args)
    raw = args.output.read_text()
    report = json.loads(raw)
    assert "private-test-key" not in raw
    assert report["status"] == "completed"
    assert (
        report["dataset_sha256"]
        == hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    )
    assert report["summary"]["decision_matches"] == 2
    assert report["summary"]["baseline_decision_matches"] == 2
    assert all(r["model"] == "test-model" for r in report["results"])
    with pytest.raises(FileExistsError):
        await evaluate.evaluate(args)
    assert len(calls) == 2


async def test_failed_experiment_preserves_completed_results(tmp_path, monkeypatch):
    monkeypatch.setenv("LMS_LLM_API_KEY", "private-test-key")

    class Classifier:
        def __init__(self, client):
            self.calls = 0

        async def classify(self, snapshot):
            self.calls += 1
            if self.calls == 2:
                raise ClassifierUnavailable("private-test-key")
            return Signals({c: 0.1 for c in Category}, "test-model", {})

    monkeypatch.setattr(evaluate, "JevClassifier", Classifier)
    args = experiment(tmp_path)
    with pytest.raises(SystemExit):
        await evaluate.evaluate(args)
    raw = args.output.read_text()
    report = json.loads(raw)
    assert report["status"] == "failed" and len(report["results"]) == 1
    assert "private-test-key" not in raw
