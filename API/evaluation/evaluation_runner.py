"""Evaluate the golden dataset and score each field as an individual check."""

import asyncio
import json
from pathlib import Path
from sklearn.metrics import f1_score

from app.structure import structure


def _norm(value):
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return sorted(_norm(item) for item in value)
    return value


def _skill_f1(actual_value, expected_value) -> float:
    actual_skills = {str(item).strip().lower() for item in (actual_value or [])}
    expected_skills = {str(item).strip().lower() for item in (expected_value or [])}

    labels = sorted(actual_skills | expected_skills)
    if not labels:
        return 1.0

    y_true = [1 if skill in expected_skills else 0 for skill in labels]
    y_pred = [1 if skill in actual_skills else 0 for skill in labels]
    return float(f1_score(y_true, y_pred, average="binary"))


def _field_score(field: str, actual_value, expected_value) -> float:
    if field in {"required_skills", "desirable_skills"}:
        return _skill_f1(actual_value, expected_value)
    return 1.0 if _norm(actual_value) == _norm(expected_value) else 0.0


def _field_passed(field: str, actual_value, expected_value) -> bool:
    if field in {"required_skills", "desirable_skills"}:
        return _skill_f1(actual_value, expected_value) == 1.0
    return _norm(actual_value) == _norm(expected_value)


def evaluate_case_checks(actual: dict | None, expected: dict) -> dict:
    checks = []
    passed_checks = 0
    total_score = 0.0

    for field, expected_value in expected.items():
        actual_value = None if actual is None else actual.get(field)
        score = _field_score(field, actual_value, expected_value)
        passed = _field_passed(field, actual_value, expected_value)

        if passed:
            passed_checks += 1
        total_score += float(score)

        checks.append(
            {
                "field": field,
                "expected": expected_value,
                "actual": actual_value,
                "score": score,
                "passed": passed,
            }
        )

    total_checks = len(checks)
    score_percent = (total_score / total_checks * 100) if total_checks else 0.0

    return {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "score_percent": score_percent,
        "checks": checks,
    }


async def evaluate_case(case: dict, runs: int = 1) -> dict:
    run_results = []
    total_checks = 0
    passed_checks = 0

    for run in range(1, runs + 1):
        try:
            actual = await asyncio.to_thread(structure, case["input"])
            result = evaluate_case_checks(actual, case["expected"])
        except Exception as exc:
            result = evaluate_case_checks({}, case["expected"])
            for check in result["checks"]:
                check["actual"] = None
                check["error"] = str(exc)

        total_checks += result["total_checks"]
        passed_checks += result["passed_checks"]

        run_results.append(
            {
                "run": run,
                "passed_checks": result["passed_checks"],
                "total_checks": result["total_checks"],
                "score_percent": result["score_percent"],
                "checks": result["checks"],
            }
        )

    score_percent = (passed_checks / total_checks * 100) if total_checks else 0.0

    return {
        "id": case["id"],
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "score_percent": score_percent,
        "runs": runs,
        "results": run_results,
    }


async def evaluate_dataset(path: str | Path | None = None, runs: int = 1) -> dict:
    dataset_path = Path(path) if path is not None else Path(__file__).with_name("golden_dataset.json")

    with dataset_path.open(encoding="utf-8") as f:
        cases = json.load(f)

    results = await asyncio.gather(*(evaluate_case(case, runs=runs) for case in cases))

    total_checks = sum(item["total_checks"] for item in results)
    passed_checks = sum(item["passed_checks"] for item in results)
    score_percent = (passed_checks / total_checks * 100) if total_checks else 0.0

    field_totals = {}
    for result in results:
        for run in result["results"]:
            for check in run["checks"]:
                field = check["field"]
                field_totals.setdefault(field, {"score_total": 0.0, "total": 0})
                field_totals[field]["total"] += 1
                field_totals[field]["score_total"] += float(check.get("score", 0.0))

    field_percentages = {
        field: (stats["score_total"] / stats["total"] * 100) if stats["total"] else 0.0
        for field, stats in sorted(field_totals.items())
    }

    return {
        "total_cases": len(cases),
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "score_percent": score_percent,
        "field_percentages": field_percentages,
        "results": results,
    }


async def main() -> int:
    summary = await evaluate_dataset(runs=1)

    lines = [
        (
            f"Overall score: {summary['score_percent']:.2f}% "
            f"({summary['passed_checks']}/{summary['total_checks']} checks passed)"
        )
    ]

    lines.append("\nPer-field summary across all test cases:")
    for field, percent in summary["field_percentages"].items():
        if field in {"required_skills", "desirable_skills"}:
            lines.append(f"  - {field}: {percent:.2f}% F1 score")
        else:
            lines.append(f"  - {field}: {percent:.2f}% pass rate")

    for result in summary["results"]:
        lines.append(
            f"\n{result['id']}: {result['score_percent']:.2f}% "
            f"({result['passed_checks']}/{result['total_checks']} checks passed)"
        )

        for run in result["results"]:
            lines.append(f"  Run {run['run']}: {run['score_percent']:.2f}%")
            for check in run["checks"]:
                status = "PASS" if check["passed"] else "FAIL"
                score_value = check.get("score", 0.0)
                if check["field"] in {"required_skills", "desirable_skills"}:
                    label = f" ({status} / F1={score_value:.2f})"
                else:
                    label = f" ({status})"
                lines.append(
                    f"    - {check['field']}{label}: "
                    f"expected={check['expected']} | actual={check['actual']}"
                )

    output = "\n".join(lines) + "\n"
    output_path = Path(__file__).with_name("evaluation_results.txt")
    output_path.write_text(output, encoding="utf-8")

    print(output, end="")
    print(f"\nResults written to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
