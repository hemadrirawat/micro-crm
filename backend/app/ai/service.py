"""Chooses a brief provider: the LLM when configured, rules otherwise or on any failure."""

from __future__ import annotations

import hashlib
import logging
from typing import Protocol

from .context import AccountContext
from .fallback import build_rules_brief
from .llm import LlmError
from .schema import AccountBrief

log = logging.getLogger(__name__)


class BriefProvider(Protocol):
    model: str

    def generate(self, ctx: AccountContext) -> AccountBrief: ...


class BriefService:
    def __init__(self, llm: BriefProvider | None):
        self.llm = llm
        self._cache: dict[str, AccountBrief] = {}

    @property
    def mode(self) -> str:
        return "llm" if self.llm else "rules"

    def brief(self, ctx: AccountContext, refresh: bool = False) -> AccountBrief:
        key = _fingerprint(ctx)
        if not refresh and key in self._cache:
            return self._cache[key]

        if self.llm is None:
            brief = build_rules_brief(ctx)
        else:
            try:
                brief = self.llm.generate(ctx)
            except LlmError as exc:
                log.warning("Falling back to rules brief for %s: %s", ctx.customer.id, exc)
                brief = build_rules_brief(ctx, fallback_reason=str(exc))
        self._cache[key] = brief
        return brief


def _fingerprint(ctx: AccountContext) -> str:
    """Cache key changes whenever the account's history or 'today' changes."""
    raw = "|".join([ctx.customer.id, ctx.customer.status.value, ctx.today.isoformat(),
                    *(f"{i.id}:{i.notes}" for i in ctx.interactions)])
    return hashlib.sha256(raw.encode()).hexdigest()
