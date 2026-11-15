"""Paid Jev experiment; run explicitly after reviewing dataset labels."""

import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path

import httpx

from src.application.ports.classifier import ClassifierUnavailable
from src.domain.entities import AdSnapshot, Policy
from src.infrastructure.jev.client import JevClassifier
from src.infrastructure.jev.questions import PROMPT_VERSION, QUESTIONS
from src.settings import Settings


def baseline(snapshot: AdSnapshot) -> bool:
    return bool(
        re.search(
            r"cvv|код из банковского|поддельн|массовое|спам спам|"
            r"реклама казино|причиню.*вред|избиени|призыв.*насили",
            snapshot.state().lower(),
        )
    )


async def evaluate(args: argparse.Namespace) -> None:
    settings = Settings()
    key = settings.lms_llm_api_key.get_secret_value()
    if not key:
        raise SystemExit("Set LMS_LLM_API_KEY locally before a paid experiment")
    raw = args.dataset.read_bytes()
    dataset = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    ids = [row["id"] for row in dataset]
    if len(ids) != len(set(ids)):
        raise SystemExit("Dataset IDs must be unique")
    rows = [row for row in dataset if row["split"] == args.split]
    if not rows:
        raise SystemExit("Selected dataset split is empty")
    policy = Policy(settings.antifraud_threshold, PROMPT_VERSION)
    report = {
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "split": args.split,
        "policy_version": policy.version,
        "threshold": policy.threshold,
        "questions": QUESTIONS,
        "status": "running",
        "results": [],
    }
    # Exclusive creation prevents accidentally overwriting an earlier experiment.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        out.write(json.dumps(report, ensure_ascii=False, indent=2))
    try:
        async with httpx.AsyncClient(
            base_url=settings.jev_base_url.rstrip("/") + "/",
            headers={"x-api-key": key},
            timeout=settings.jev_timeout_seconds,
        ) as client:
            classifier = JevClassifier(client)
            for number, row in enumerate(rows, 1):
                snapshot = AdSnapshot(ad_id=number, user_id=1, **row["ad"])
                signals = await classifier.classify(snapshot)
                d = policy.decide(signals)
                expected = row["expected"]
                report["results"].append(
                    {
                        "id": row["id"],
                        "model": signals.model,
                        "scores": signals.scores,
                        "usage": signals.usage,
                        "blocked": d.blocked,
                        "categories": list(d.categories),
                        "reason": d.reason,
                        "expected": expected,
                        "decision_correct": d.blocked == expected["blocked"],
                        "correct": d.blocked == expected["blocked"]
                        and set(d.categories) == set(expected["categories"]),
                        "baseline_blocked": baseline(snapshot),
                        "baseline_correct": baseline(snapshot) == expected["blocked"],
                    }
                )
                args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        report["status"] = "completed"
    except ClassifierUnavailable:
        report["status"] = "failed"
        raise SystemExit(
            "Jev call failed; partial results were saved without secrets"
        ) from None
    finally:
        results = report["results"]
        report["summary"] = {
            "count": len(results),
            "category_exact_matches": sum(x["correct"] for x in results),
            "decision_matches": sum(x["decision_correct"] for x in results),
            "baseline_decision_matches": sum(x["baseline_correct"] for x in results),
        }
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=["train", "holdout"], required=True)
    asyncio.run(evaluate(parser.parse_args()))
