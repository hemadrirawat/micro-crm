"""Lightweight, deterministic understanding of interaction notes.

Everything here is pattern-based on purpose: it is fast, explainable, testable and
works without an API key. The patterns describe *kinds* of relationship events
(a question, a proposal being sent, a hold instruction), not specific accounts.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

from ..models import Interaction, InteractionType

MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
_MONTH = r"(january|february|march|april|may|june|july|august|september|october|november|december)"


def rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# --- direction ---------------------------------------------------------------------
OUTBOUND_START = rx(
    r"^(sent|shared|explained|checked in|discussed|followed up|called|emailed|replied to"
    r"|follow-up completed|scheduled|booked)\b"
)
INBOUND_VERB = rx(
    r"\b(asked|asking|requested|replied|responded|said|mentioned|confirmed|reported"
    r"|thanked|filled out|explained|expects?)\b"
)

# --- asks from the account -----------------------------------------------------------
FOLLOW_UP_REQUEST = rx(
    r"\b(schedule|set up|book)\b.{0,40}\b(follow-?up|call|meeting|chat)\b"
    r"|\brequested an? (call|follow-?up|meeting)\b"
)
QUESTION = rx(r"\b(asked|asking)\s+(whether|if|about|for)\b|\bwanted to (understand|know)\b")
QUESTION_CLAUSE = rx(r"\b(?:asked|asking)\s+(whether|if|about|for)\s+(.+)$")
FOLLOW_UP_TOPIC = rx(r"\bto discuss ([\w\s-]+?)(?:[.,]|$)")

# --- deal stage ------------------------------------------------------------------
DEMO_DONE = rx(r"\bdemo (completed|went well)\b|\bdemo with\b")
DEMO_LINK_SENT = rx(r"^sent\b.*\bdemo\b.*\b(link|invite|times?)\b")
DEMO_NOT_SCHEDULED = rx(r"\bnever scheduled the demo\b|\bdemo (was |is )?not (yet )?scheduled\b")
DELIVERABLE_KINDS: list[tuple[str, re.Pattern[str]]] = [
    ("proposal", rx(r"^sent\b.*\bproposal\b")),
    ("contract details", rx(r"^sent\b.*\bcontract\b")),
    ("pricing", rx(r"^sent\b.*\bpricing\b")),
    ("customer reference", rx(r"^sent\b.*\b(reference|case study)\b")),
]
IMPLEMENTATION = rx(r"\bimplementation\b|\bonboarding\b|\bgo[- ]live\b|\brollout\b")
EXPANSION = rx(
    r"\b(two|three|four|five|six|seven|eight|nine|ten|\d+)[- ]locations?\b"
    r"|\b(second|third|another|new|additional) (office|location|account|practice)\b"
    r"|\bmulti-?location\b"
)
LOCATION_COUNT = rx(r"\b(two|three|four|five|six|seven|eight|nine|ten|\d+)[- ]locations?\b")

# --- timing ------------------------------------------------------------------------
DEADLINE = rx(rf"\b(?:before|by)\s+{_MONTH}\s+(\d{{1,2}})\b")
DECISION_MONTH = rx(rf"\bdecision\b[^.]*?\b(?:in|by)\s+{_MONTH}\b")
HOLD_UNTIL_MONTH = rx(rf"\b(?:until|before)\s+(?:their\s+|the\s+|our\s+)?{_MONTH}\b")
MONTH_MENTION = rx(rf"\bin\s+{_MONTH}\b")

# --- intent & sentiment --------------------------------------------------------------
INTENT_PHRASES: list[tuple[re.Pattern[str], int]] = [
    (rx(r"\bhigh[- ]intent\b"), 3),
    (rx(r"\basked for a proposal\b"), 3),
    (rx(r"\b(looks|seems) reasonable\b"), 2),
    (rx(r"\bwent well\b"), 2),
    (rx(r"\brequested a demo\b"), 2),
    (rx(r"\b(asking|asked) (for|about) pricing\b"), 2),
    (rx(r"\bcontract length\b|\bcancellation terms\b"), 2),
    (rx(r"\b(asked for|requested) (a )?(customer )?reference\b"), 2),
    (rx(r"\bexpects? to (make a )?decision\b|\bexpects? to decide\b"), 1),
    (rx(r"\basked for more information\b|\bresponded to\b"), 1),
    (rx(r"\bstill interested\b"), 1),
    (rx(r"\binterested\b"), 1),
    (rx(r"\bliked\b"), 1),
]
POSITIVE = rx(
    r"\bhappy\b|\bimproved\b|\bpositive\b|\bsatisfied\b|\bseems? better\b|\bliked\b"
    r"|\bbetter than expected\b|\bwent well\b|\breduced\b.{0,25}\bnoticeably\b"
)
ISSUE = rx(
    r"\bincorrect\b|\bhang up\b|\berrors?\b|\bbroken\b|\bnot working\b|\bcomplain"
    r"|\bissues?\b|\bproblems?\b|\bbugs?\b|\bdelays?\b"
)
RESOLVED = rx(r"\bimproved\b|\bseems? better\b|\bresolved\b|\bfixed\b|\bpositive\b|\bbetter than expected\b")
OBJECTION = rx(r"\bconcerned about\b|\bworried\b|\bhesitant\b|\bskeptical\b")
APPROVAL = rx(r"\bneeds? (approval|sign-?off)\b")
BUDGET = rx(r"\bbudget\w*\b.{0,30}\b(delayed|frozen|cut|on hold)\b")

# --- internal instructions (usually in notes) ----------------------------------------
HOLD = rx(r"\bdo not push\b|\bdon'?t push\b|\bhold off\b|\bdelayed until\b")
NO_FOLLOW_UP = rx(r"\bno (additional |further )?follow-?up (is )?(required|needed)\b|\bno action (required|needed)\b")
INTERNAL_FLAG = rx(r"\bfollow-?up may be appropriate\b|\bneed to (confirm|follow up|send|schedule|check)\b")
NEED_TO = rx(r"^need to (.+?)\.?$")
STALL = rx(
    r"\bno (response|reply)\b|\bno follow-?up has been sent\b|\binactive for\b"
    r"|\bhas not responded\b|\bgone quiet\b"
)

# --- fact extraction --------------------------------------------------------------
FACT_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("Scale", rx(r"\b\d+%|\b\d+ (missed )?calls\b|\blocations?\b|\breceptionists?\b|\bproviders?\b|\boffice\b")),
    ("Needs", rx(r"\bstruggles?\b|\bmiss(ed)? calls\b|\bvoicemail\b|\bworkload\b"
                 r"|\binterested in\b|\bimportant\b|\bliked\b")),
    ("Sentiment", rx(r"\bhappy\b|\bimproved\b|\bpositive\b|\bsatisfied\b|\bbetter\b|\bnoticeably\b")),
    ("Integration", rx(r"\bintegrat\w*\b|\bdentrix\b|\bspanish\b|\bsms\b|\breport\w*\b")),
    ("Timeline", rx(rf"\b{_MONTH}\b|\bnext year\b")),
    ("Decision", rx(r"\bapproval\b|\bdecision\b|\bbudget\w*\b|\bpartners\b|\bcontract\b")),
    ("Concern", rx(r"\bconcern\w*\b|\bworried\b|\bincorrect\b|\bhang up\b")),
]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def month_number(name: str) -> int:
    return MONTHS[name.lower()]


def end_of_month(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def infer_year(month: int, reference: date) -> int:
    """A month mentioned in a note refers to the next occurrence from the note's date."""
    return reference.year + 1 if month < reference.month else reference.year


def fmt_date(d: date) -> str:
    return f"{calendar.month_abbr[d.month]} {d.day}"


def first_name(full_name: str | None) -> str:
    return full_name.split(" ")[0] if full_name else "the account"


@dataclass(frozen=True)
class Touch:
    """An interaction annotated with who was talking.

    `ours`   — we reached out, delivered something, or held a live conversation.
    `theirs` — the account said or asked something.
    Calls and meetings are two-way, so they are both. Internal notes are neither.
    """

    interaction: Interaction
    index: int
    ours: bool
    theirs: bool
    sentences: tuple[str, ...]

    @property
    def is_note(self) -> bool:
        return self.interaction.type == InteractionType.NOTE

    def their_sentences(self) -> list[str]:
        """Sentences that report what the account said (outbound sentences excluded)."""
        if self.is_note:
            return []
        return [s for s in self.sentences if not OUTBOUND_START.search(s)]


def classify(interaction: Interaction, index: int) -> Touch:
    parts = tuple(sentences(interaction.notes))
    if interaction.type == InteractionType.NOTE:
        return Touch(interaction, index, ours=False, theirs=False, sentences=parts)
    if interaction.type in (InteractionType.CALL, InteractionType.MEETING):
        return Touch(interaction, index, ours=True, theirs=True, sentences=parts)
    ours = any(OUTBOUND_START.search(s) for s in parts)
    theirs = any(INBOUND_VERB.search(s) for s in parts if not OUTBOUND_START.search(s))
    if not ours and not theirs:
        theirs = True  # an email with no outbound verb is most likely from the account
    return Touch(interaction, index, ours=ours, theirs=theirs, sentences=parts)


def question_clause(sentence: str) -> tuple[str, str] | None:
    """'Emily asked whether SMS support is planned because…' -> ('whether', 'SMS support is planned')."""
    match = QUESTION_CLAUSE.search(sentence)
    if not match:
        return None
    connector, rest = match.group(1).lower(), match.group(2)
    rest = re.split(r"\s+because\s+|\s+and\s+(?:wanted|said|mentioned)\s+", rest)[0]
    rest = rest.rstrip(" .?!")
    return ("whether" if connector == "if" else connector), rest
