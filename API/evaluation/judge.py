def _norm(v):
    if isinstance(v, str):
        return v.strip().lower()
    if isinstance(v, list):
        return sorted(_norm(x) for x in v)
    return v


def judge(actual: dict, expected: dict) -> dict:
    if actual is None:
        return {"passed": False, "diff": "no output"}

    diff = {
        k: {"expected": expected[k], "actual": actual.get(k)}
        for k in expected
        if _norm(actual.get(k)) != _norm(expected[k])
    }
    return {"passed": not diff, "diff": diff}