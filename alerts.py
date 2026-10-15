#!/usr/bin/env python3
"""Price Alert Tool for the Wissen Technology campus assessment."""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


class InputError(ValueError):
    """Raised when an input file is malformed or a rule is invalid."""


@dataclass(frozen=True)
class Price:
    day: date
    instrument: str
    close: float


@dataclass(frozen=True)
class Alert:
    day: date
    rule_id: str
    instrument: str
    description: str


def read_prices(path: str | Path) -> list[Price]:
    prices: list[Price] = []
    seen: set[tuple[date, str]] = set()
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {"date", "instrument", "close"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise InputError("prices CSV must contain date,instrument,close columns")
            for line_number, row in enumerate(reader, start=2):
                try:
                    day = date.fromisoformat((row.get("date") or "").strip())
                    instrument = (row.get("instrument") or "").strip()
                    close_text = (row.get("close") or "").strip()
                    close = float(close_text)
                    if not instrument:
                        raise ValueError("instrument cannot be empty")
                    if not close_text or not __import__("math").isfinite(close) or close < 0:
                        raise ValueError("close must be a finite, non-negative number")
                except (ValueError, TypeError) as exc:
                    raise InputError(f"invalid prices CSV row {line_number}: {exc}") from exc
                key = (day, instrument)
                if key in seen:
                    raise InputError(f"duplicate price for {instrument} on {day.isoformat()}")
                seen.add(key)
                prices.append(Price(day, instrument, close))
    except OSError as exc:
        raise InputError(f"cannot read prices file '{path}': {exc.strerror or exc}") from exc
    return sorted(prices, key=lambda p: (p.instrument, p.day))


def read_rules(path: str | Path) -> list[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as handle:
            rules = json.load(handle)
    except OSError as exc:
        raise InputError(f"cannot read rules file '{path}': {exc.strerror or exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"rules file is not valid JSON: {exc}") from exc
    if not isinstance(rules, list):
        raise InputError("rules JSON must be a list of rule objects")
    seen_ids: set[str] = set()
    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            raise InputError(f"rule {index} must be a JSON object")
        rule_id = rule.get("id")
        instrument = rule.get("instrument")
        kind = rule.get("type")
        direction = rule.get("direction")
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise InputError(f"rule {index}: id must be a non-empty string")
        if rule_id in seen_ids:
            raise InputError(f"duplicate rule id: {rule_id}")
        seen_ids.add(rule_id)
        if not isinstance(instrument, str) or not instrument.strip():
            raise InputError(f"rule {rule_id}: instrument must be a non-empty string")
        if direction not in {"above", "below"}:
            raise InputError(f"rule {rule_id}: direction must be 'above' or 'below'")
        if kind == "level":
            if not _positive_number(rule.get("level")):
                raise InputError(f"rule {rule_id}: level must be a finite non-negative number")
        elif kind == "ma_cross":
            short, long = rule.get("short"), rule.get("long")
            if not isinstance(short, int) or isinstance(short, bool) or short < 1:
                raise InputError(f"rule {rule_id}: short must be a positive integer")
            if not isinstance(long, int) or isinstance(long, bool) or long < 1:
                raise InputError(f"rule {rule_id}: long must be a positive integer")
            if short >= long:
                raise InputError(f"rule {rule_id}: short must be smaller than long")
        else:
            raise InputError(f"rule {rule_id}: type must be 'level' or 'ma_cross'")
    return rules


def _positive_number(value: Any) -> bool:
    import math
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def find_alerts(prices: list[Price], rules: list[dict[str, Any]]) -> list[Alert]:
    by_instrument: dict[str, list[Price]] = {}
    for price in prices:
        by_instrument.setdefault(price.instrument, []).append(price)
    for series in by_instrument.values():
        series.sort(key=lambda p: p.day)

    alerts: list[Alert] = []
    for rule in rules:
        series = by_instrument.get(rule["instrument"], [])
        kind, direction = rule["type"], rule["direction"]
        if kind == "level":
            level = float(rule["level"])
            previous: float | None = None
            for price in series:
                crossed = previous is not None and (
                    (direction == "below" and previous >= level and price.close < level)
                    or (direction == "above" and previous <= level and price.close > level)
                )
                if crossed:
                    alerts.append(Alert(price.day, rule["id"], price.instrument,
                                        f"level {direction} {_format_number(level)}"))
                previous = price.close
        else:
            short_n, long_n = rule["short"], rule["long"]
            closes: list[float] = []
            previous_short: float | None = None
            previous_long: float | None = None
            for price in series:
                closes.append(price.close)
                current_short = sum(closes[-short_n:]) / short_n if len(closes) >= short_n else None
                current_long = sum(closes[-long_n:]) / long_n if len(closes) >= long_n else None
                crossed = False
                if (previous_short is not None and previous_long is not None
                        and current_short is not None and current_long is not None):
                    crossed = (
                        (direction == "above" and previous_short <= previous_long and current_short > current_long)
                        or (direction == "below" and previous_short >= previous_long and current_short < current_long)
                    )
                if crossed:
                    alerts.append(Alert(price.day, rule["id"], price.instrument,
                                        f"ma_cross {short_n}/{long_n} {direction}"))
                previous_short, previous_long = current_short, current_long

    return sorted(alerts, key=lambda a: (a.day, a.rule_id))


def _format_number(number: float) -> str:
    return str(int(number)) if number.is_integer() else f"{number:g}"


def format_alert(alert: Alert) -> str:
    return f"{alert.day.isoformat()}  {alert.rule_id}  {alert.instrument}  {alert.description}"


def run(prices_path: str, rules_path: str) -> int:
    prices = read_prices(prices_path)
    rules = read_rules(rules_path)
    for alert in find_alerts(prices, rules):
        print(format_alert(alert))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] in {"-h", "--help"}:
        print("Usage: python alerts.py prices.csv rules.json")
        return 0 if args and args[0] in {"-h", "--help"} else 2
    try:
        return run(args[0], args[1])
    except InputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
