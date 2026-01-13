#!/usr/bin/env python3
from datetime import datetime, timezone
from typing import Any
import json
import requests

# click on the stop you want at https://ucf.transloc.com/routes
# grab the last number there e.g. https://ucf.transloc.com/routes/4/stops/6
STOP_IDS = "6,7" # comma separated list of interested stops

API_HOST = "https://ucf.transloc.com"
API_PATH = "/Services/JSONPRelay.svc/GetStopArrivalTimes"
API_KEY = "" # seems to work just fine without an api key
VERSION = "2"
TIMEOUT_SECS = 10


def fetch_stop_arrival_times() -> Any:
    url = f"{API_HOST}{API_PATH}"
    params = {"apiKey": API_KEY, "stopIds": STOP_IDS, "version": VERSION}
    headers = {"Accept": "application/json"}
    r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT_SECS)
    r.raise_for_status()
    return r.json()


def parse_arrivals(api_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(api_payload, list):
        return []

    arrivals: list[dict[str, Any]] = []

    for route_block in api_payload:
        if not isinstance(route_block, dict):
            continue

        route_desc = route_block.get("RouteDescription")
        route_id = route_block.get("RouteId")
        stop_desc = route_block.get("StopDescription")
        stop_id = route_block.get("StopId")

        times = route_block.get("Times") or []
        if not isinstance(times, list) or not times:
            continue

        for t in times:
            if not isinstance(t, dict):
                continue

            try:
                seconds = int(t.get("Seconds"))
            except Exception:
                continue

            is_arriving = bool(t.get("IsArriving", False))
            text = (t.get("Text") or "").strip().lower()

            arrivals.append({
                "route": route_desc,
                "route_id": route_id,
                "vehicle_id": t.get("VehicleId"),
                "minutes": (seconds + 59) // 60,
                "status": "Arriving" if is_arriving or text == "arriving" else "En route",
                "stop": stop_desc,
                "stop_id": stop_id,
            })

    arrivals.sort(key=lambda x: x["minutes"])
    return arrivals


def build_homeassistant_json(api_payload: Any) -> dict[str, Any]:
    arrivals = parse_arrivals(api_payload)

    by_stop: dict[Any, dict[str, Any]] = {}
    for a in arrivals:
        sid = a["stop_id"]
        s = by_stop.setdefault(sid, {"stop_id": sid, "stop": a["stop"], "etas": []})
        s["etas"].append({
            "route": a["route"],
            "route_id": a["route_id"],
            "vehicle_id": a["vehicle_id"],
            "minutes": a["minutes"],
            "status": a["status"],
        })

    stops: list[dict[str, Any]] = []
    for s in by_stop.values():
        s["etas"].sort(key=lambda e: e["minutes"])
        s["next_minutes"] = s["etas"][0]["minutes"] if s["etas"] else None
        s["routes_present"] = sorted({e["route"] for e in s["etas"] if e.get("route")})
        stops.append(s)

    stops.sort(key=lambda s: (s["next_minutes"] is None, s["next_minutes"] or 10**9, str(s["stop_id"])))

    top_stop = stops[0] if stops and stops[0]["next_minutes"] is not None else None

    return {
        "next_minutes": top_stop["next_minutes"] if top_stop else None,
        "stop": top_stop["stop"] if top_stop else None,
        "stop_id": top_stop["stop_id"] if top_stop else None,
        "stops": stops,
    }


def main() -> None:
    try:
        out = build_homeassistant_json(fetch_stop_arrival_times())
        print(json.dumps(out, separators=(",", ":")))
    except Exception as e:
        print(json.dumps({
            "next_minutes": None,
            "stop": None,
            "stop_id": None,
            "stops": [],
            "routes_present": [],
            "error": str(e),
        }, separators=(",", ":")))


if __name__ == "__main__":
    main()
