"""Read-only charts for synthetic election practice; no official data or forecasting.

Input: snapshot from existing election engine and bounded historical snapshots.
Output: auditable JSON tables and graph data. Does not mutate any election state.
"""
from __future__ import annotations

from statistics import mean, median, pstdev
from typing import Any

METHODS = {
    "vote_share": ("후보별 득표 비교", "후보별 득표수·득표율", "막대그래프"),
    "progress_compare": ("지역별 개표 진행률", "목표 모의 투표수 대비 집계 비율", "막대그래프"),
    "lead_margin": ("선거구별 선두 격차", "각 선거구 1·2위 득표율 차이(%p)", "막대그래프"),
    "progress_distribution": ("개표율 분포", "해당 범위 선거구의 10%p 구간별 빈도", "히스토그램"),
    "progress_trend": ("개표 진행 추이", "집계 단계별 모의 개표율", "꺾은선그래프"),
    "candidate_trend": ("후보별 누적 표수 추이", "집계 단계별 후보 A·B·C 누적 표수", "꺾은선그래프"),
    "increment_trend": ("단계별 추가 집계량", "직전 단계 대비 추가된 표수", "꺾은선그래프"),
    "progress_margin_scatter": ("개표율·선두 격차 산점도", "선거구별 개표율과 1·2위 득표율 격차", "산점도"),
}

CANDIDATES = ("모의 후보 A", "모의 후보 B", "모의 후보 C")
LIMIT_HISTORY = 121


def compact_history(snap: dict) -> dict:
    """Keep 120 recent *simulated* updates; stable when re-rendering charts."""
    def tiny(v):
        return {"counted": int(v["counted"]), "progress_pct": float(v["progress_pct"]),
                "votes": list(v["votes"])}
    return {"step": snap["step"], "updated_at": snap["updated_at"],
            "national": tiny(snap["national"]),
            "regions": {x["id"]: tiny(x) for x in snap["regions"]},
            "districts": {x["id"]: tiny(x) for x in snap["districts"]}}


def _scope_value(snap: dict, scope: str, region: str | None, district: str | None):
    if scope == "national":
        return "전국", snap["national"], list(snap["districts"]), "national", None
    if scope == "region":
        obj = next((x for x in snap["regions"] if x["id"] == region), None)
        if obj is None:
            raise ValueError("해당 시·도가 없습니다")
        return obj["full_name"], obj, [x for x in snap["districts"] if x["region"] == region], "regions", region
    if scope == "district":
        obj = next((x for x in snap["districts"] if x["id"] == district), None)
        if obj is None:
            raise ValueError("해당 모의 선거구가 없습니다")
        if region and region != obj["region"]:
            raise ValueError("선택한 시·도와 모의 선거구가 다릅니다")
        return obj["name"], obj, [obj], "districts", district
    raise ValueError("분석 범위는 national, region, district 중 하나여야 합니다")


def _historic_value(point: dict, kind: str, key: str | None):
    return point["national"] if kind == "national" else point[kind][key]


def _margin(votes: list[int]) -> float:
    total = sum(votes)
    if not total:
        return 0.0
    vals = sorted(votes, reverse=True)
    return round((vals[0] - vals[1]) / total * 100, 2)


def _stat_summary(districts: list[dict]) -> dict:
    values = [float(d["progress_pct"]) for d in districts]
    return {"district_count": len(values),
            "mean_district_progress_pct": round(mean(values), 2) if values else 0,
            "median_district_progress_pct": round(median(values), 2) if values else 0,
            "population_std_district_progress_pp": round(pstdev(values), 2) if values else 0}


def analyze(snap: dict, history: list[dict], *, method: str = "vote_share",
            scope: str = "national", region: str | None = None,
            district_id: str | None = None, window: int = 30) -> dict[str, Any]:
    if method not in METHODS:
        raise ValueError("지원하지 않는 통계 분석 기법")
    if type(window) is not int or not 2 <= window <= 120:
        raise ValueError("이력 범위는 2~120 단계입니다")
    title, entity, districts, kind, key = _scope_value(snap, scope, region, district_id)
    recent = history[-window:]
    chart: dict[str, Any] = {"kind": "bar", "labels": [], "series": [], "unit": ""}
    columns, rows = [], []
    caveat = "모든 수치는 교육용 난수 생성 결과입니다. 실제 선거 결과·출구조사·당선 예측이 아닙니다."

    if method == "vote_share":
        total = int(entity["counted"])
        rows = [{"candidate": c, "votes": entity["votes"][i],
                 "percent": round(entity["votes"][i]/total*100, 2) if total else 0}
                for i, c in enumerate(CANDIDATES)]
        columns = [("candidate", "모의 후보"), ("votes", "집계 표수"), ("percent", "득표율 (%)")]
        chart = {"kind": "bar", "labels": [r["candidate"] for r in rows],
                 "series": [{"name": "득표율", "values": [r["percent"] for r in rows]}], "unit": "%", "max_hint": 100}
    elif method == "progress_compare":
        if scope == "national":
            items = [(r["full_name"], r) for r in snap["regions"]]
        else:
            items = [(d["name"], d) for d in districts]
        rows = [{"area": label, "progress_pct": float(x["progress_pct"]),
                 "counted": int(x["counted"])} for label, x in items]
        rows.sort(key=lambda x: (-x["progress_pct"], x["area"]))
        columns = [("area", "대상"), ("progress_pct", "개표율 (%)"), ("counted", "집계 표수")]
        chart = {"kind": "bar", "labels": [r["area"] for r in rows[:20]],
                 "series": [{"name": "개표율", "values": [r["progress_pct"] for r in rows[:20]]}],
                 "unit": "%", "max_hint": 100}
        caveat += " 개표율은 선거구별 목표 모의 투표수 대비 집계표수입니다."
    elif method == "lead_margin":
        rows = [{"district": d["name"], "progress_pct": d["progress_pct"],
                 "margin_pp": _margin(d["votes"])} for d in districts]
        rows.sort(key=lambda x: (-x["margin_pp"], x["district"]))
        columns = [("district", "모의 선거구"), ("progress_pct", "개표율 (%)"),
                   ("margin_pp", "1·2위 격차 (%p)")]
        chart = {"kind": "bar", "labels": [r["district"] for r in rows[:20]],
                 "series": [{"name": "1·2위 격차", "values": [r["margin_pp"] for r in rows[:20]]}],
                 "unit": "%p", "max_hint": 100}
    elif method == "progress_distribution":
        counts = [0] * 10
        for d in districts:
            counts[min(9, int(float(d["progress_pct"]) // 10))] += 1
        rows = [{"bin": f"{i*10}~{(i+1)*10 if i<9 else 100}%", "districts": n}
                for i, n in enumerate(counts)]
        columns = [("bin", "개표율 구간"), ("districts", "선거구 수")]
        chart = {"kind": "bar", "labels": [r["bin"] for r in rows],
                 "series": [{"name": "선거구 수", "values": counts}], "unit": "개", "max_hint": None}
        caveat += " 구간별 빈도는 독립 선거구 수이며 표수 가중치가 없습니다."
    elif method in ("progress_trend", "candidate_trend", "increment_trend"):
        points = [(_historic_value(p, kind, key), p["step"], p["updated_at"]) for p in recent]
        labels = [str(step) for _, step, _ in points]
        if method == "progress_trend":
            rows = [{"step": step, "updated_at": at, "progress_pct": v["progress_pct"]}
                    for v, step, at in points]
            columns = [("step", "집계 단계"), ("updated_at", "기준 시각"), ("progress_pct", "개표율 (%)")]
            chart = {"kind": "line", "labels": labels,
                     "series": [{"name": "개표율", "values": [r["progress_pct"] for r in rows]}], "unit": "%", "max_hint": 100}
        elif method == "candidate_trend":
            rows = [{"step": step, "updated_at": at, "candidate_A": v["votes"][0],
                     "candidate_B": v["votes"][1], "candidate_C": v["votes"][2]}
                    for v, step, at in points]
            columns = [("step", "집계 단계"), ("updated_at", "기준 시각"),
                       ("candidate_A", "후보 A 표수"), ("candidate_B", "후보 B 표수"),
                       ("candidate_C", "후보 C 표수")]
            chart = {"kind": "line", "labels": labels,
                     "series": [{"name": CANDIDATES[i], "values": [p[0]["votes"][i] for p in points]}
                                for i in range(3)], "unit": "표", "max_hint": None}
        else:
            rows = [{"step": cur[1], "updated_at": cur[2],
                     "new_votes": cur[0]["counted"] - prev[0]["counted"]}
                    for prev, cur in zip(points, points[1:])]
            columns = [("step", "집계 단계"), ("updated_at", "기준 시각"), ("new_votes", "추가 집계 표수")]
            chart = {"kind": "line", "labels": [str(r["step"]) for r in rows],
                     "series": [{"name": "신규 집계", "values": [r["new_votes"] for r in rows]}],
                     "unit": "표", "max_hint": None}
        caveat += " 최근 120개 단계 이력만 서버 메모리에 저장하며 재시작하면 초기화됩니다."
    else:
        rows = [{"district": d["name"], "progress_pct": d["progress_pct"],
                 "margin_pp": _margin(d["votes"])} for d in districts]
        columns = [("district", "모의 선거구"), ("progress_pct", "개표율 (%)"),
                   ("margin_pp", "1·2위 격차 (%p)")]
        chart = {"kind": "scatter", "points": [{"x": r["progress_pct"], "y": r["margin_pp"],
                                                 "label": r["district"]} for r in rows],
                 "x_label": "모의 개표율 (%)", "y_label": "1·2위 격차 (%p)"}
        caveat += " 난수로 만든 값들 사이의 상관을 실제 투표 행동이나 인과관계로 해석하면 안 됩니다."
    return {"mode": "SIMULATION_ONLY", "source": snap["source"],
            "step": snap["step"], "updated_at": snap["updated_at"],
            "scope": scope, "scope_label": title, "method": method,
            "method_label": METHODS[method][0], "method_description": METHODS[method][1],
            "chart": chart, "columns": [{"key": k, "label": n} for k, n in columns],
            "rows": rows, "summary": {"counted": entity["counted"],
                                    "weighted_progress_pct": entity["progress_pct"],
                                    **_stat_summary(districts)},
            "history_points": len(recent), "caveat": caveat,
            "no_prediction": True}
