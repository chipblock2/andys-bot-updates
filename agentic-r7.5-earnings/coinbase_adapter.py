#!/usr/bin/env python3
"""Helpers for feeding Coinbase Advanced account data into R7.5.

Expected authenticated endpoint:
GET https://api.coinbase.com/api/v3/brokerage/transaction_summary

This module intentionally contains no API secret and no order-placement code.
The existing bot can pass the decoded JSON response into the earnings engine.
"""
from __future__ import annotations

from typing import Any


def normalize_transaction_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    tier = payload.get("fee_tier") or {}
    return {
        "total_volume": payload.get("total_volume"),
        "total_fees": payload.get("total_fees"),
        "advanced_trade_only_volume": payload.get("advanced_trade_only_volume"),
        "advanced_trade_only_fees": payload.get("advanced_trade_only_fees"),
        "fee_tier": {
            "pricing_tier": tier.get("pricing_tier"),
            "usd_from": tier.get("usd_from"),
            "usd_to": tier.get("usd_to"),
            "maker_fee_rate": tier.get("maker_fee_rate"),
            "taker_fee_rate": tier.get("taker_fee_rate"),
        },
    }


def normalize_book(best_bid: float, best_ask: float, bid_depth_gbp: float,
                   ask_depth_gbp: float, market_status: str = "FULL_TRADING") -> dict:
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "bid_depth_gbp": bid_depth_gbp,
        "ask_depth_gbp": ask_depth_gbp,
        "market_status": market_status,
    }
