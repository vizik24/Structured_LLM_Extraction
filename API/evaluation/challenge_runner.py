"""Run the challenge set against the real model."""

import asyncio
import json
from pathlib import Path

from app.structure import structure
from evaluation.judge import judge


async def evaluate_case(case: dict, runs: int = 5) -> dict:
    run_results = []

    for run in range(1, runs + 1):
        try:
            actual = await asyncio.to_thread(structure, case["input"])
            verdict = judge(actual, case["expected"])
            passed = verdict["passed"]
            diff = verdict.get("diff")
        except Exception as exc:
            passed = False
            diff = f"{type(exc).__name__}: {exc}"

        run_results.append({
            "run": run,
            "passed": passed,
            "diff": diff,
        })

        print(f"[{ 'PASS' if passed else 'FAIL' }] {case['id']} run {run}/{runs}")
        if not passed:
            print(f"  diff: {diff}")

    case_passed = all(item["passed"] for item in run_results)
    result = {
        "id": case["id"],
        "passed": case_passed,
        "runs": runs,
        "results": run_results,
    }
    return result


async def main() -> int:
    file_path = Path(__file__).with_name("test_set.json")
    with file_path.open(encoding="utf-8") as f:
        cases = json.load(f)

    results = await asyncio.gather(*(evaluate_case(case, runs=5) for case in cases))
    passed_cases = sum(1 for r in results if r["passed"])

    lines = [f"{passed_cases}/{len(cases)} cases passed across 5 runs each\n"]
    for result in results:
        lines.append(f"{result['id']}: {'PASS' if result['passed'] else 'FAIL'}")
        for item in result["results"]:
            lines.append(f"  run {item['run']}: {'PASS' if item['passed'] else 'FAIL'}")
            if not item["passed"]:
                lines.append(f"    diff: {item['diff']}")

    summary_path = Path(__file__).with_name("challenge_results.txt")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n{passed_cases}/{len(cases)} cases passed")
    print(f"Results written to {summary_path}")
    return 0 if passed_cases == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
