"""
Live transaction simulator. Generates a continuous, plausible stream of bank
transfers — mostly clean, occasionally part of a mule-network layering chain
or a velocity burst — so the rule engine (aci/cybercrime/rules.py) has real
patterns to catch rather than being fed transactions that are pre-labelled.
Nothing here is a real transaction from any real bank; every account number,
city, and amount is generated.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from aci.cybercrime.data import CITIES
from aci.cybercrime.models import LiveTransaction
from aci.cybercrime.rules import MULE_ACCOUNT_BLACKLIST, VELOCITY_WINDOW, evaluate

CHANNELS = ["NEFT", "RTGS", "IMPS", "UPI"]
_MULES = sorted(MULE_ACCOUNT_BLACKLIST)


class TransactionSimulator:
    """Stateful generator: tracks recent transactions per source account (for
    the velocity rule) and in-progress layering chains (so a mule-network
    case's money genuinely hops source -> mule1 -> mule2 -> cash-out across
    successive ticks, rather than each event being independent)."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self._counter = 0
        self._recent_by_source: dict[str, list[LiveTransaction]] = {}
        self._active_chain: list[str] | None = None  # remaining hops of an in-progress layering chain
        self._chain_source: str | None = None
        self._chain_hop = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"LTX-{self._counter:06d}"

    def _prune_recent(self, account: str, now: datetime) -> list[LiveTransaction]:
        window_start = now - VELOCITY_WINDOW
        kept = [t for t in self._recent_by_source.get(account, []) if t.ts >= window_start]
        self._recent_by_source[account] = kept
        return kept

    def _start_layering_chain(self) -> None:
        source = f"AC-VICTIM-{self.rng.randint(1000, 9999)}"
        mule1, mule2 = self.rng.sample(_MULES, 2)
        cashout = f"CRYPTO-WALLET-{self.rng.randint(1000, 9999):04X}"
        self._active_chain = [source, mule1, mule2, cashout]
        self._chain_source = source
        self._chain_hop = 0

    def tick(self) -> LiveTransaction:
        now = datetime.now(timezone.utc)
        city, _, lat, lng = self.rng.choice(CITIES)

        # ~12% chance to start a new layering chain if none is in progress —
        # keeps the IO Case Ops view showing real hop-by-hop progress rather
        # than a chain that completes in one tick.
        if self._active_chain is None and self.rng.random() < 0.12:
            self._start_layering_chain()

        if self._active_chain is not None and self._chain_hop < len(self._active_chain) - 1:
            src = self._active_chain[self._chain_hop]
            dst = self._active_chain[self._chain_hop + 1]
            hop_index = self._chain_hop
            amount = int(self.rng.uniform(150_000, 900_000))
            self._chain_hop += 1
            if self._chain_hop >= len(self._active_chain) - 1:
                self._active_chain = None  # chain complete after this tick
        else:
            # An ordinary, unrelated transfer — occasionally re-using a source
            # account quickly enough to trip the velocity rule on its own.
            burst = self.rng.random() < 0.08
            src = (self.rng.choice(list(self._recent_by_source.keys())) if burst and self._recent_by_source
                   else f"AC-{self.rng.randint(10000, 99999)}")
            dst = f"AC-{self.rng.randint(10000, 99999)}"
            hop_index = 0
            amount = int(self.rng.choice([
                self.rng.uniform(500, 50_000),          # routine
                self.rng.uniform(50_000, 300_000),       # notable
                self.rng.uniform(300_000, 1_200_000),    # high value
            ]))

        txn = LiveTransaction(
            tx_id=self._next_id(), ts=now, source_account=src, destination_account=dst,
            amount=amount, channel=self.rng.choice(CHANNELS), city=city, lat=round(lat, 4), lng=round(lng, 4),
            hop_index=hop_index,
        )

        recent = self._prune_recent(src, now)
        flagged, reasons, score = evaluate(txn, recent)
        txn.flagged, txn.flag_reasons, txn.risk_score = flagged, reasons, score
        self._recent_by_source.setdefault(src, []).append(txn)
        return txn
