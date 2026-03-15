"""Tree-based SCPI command router with short-form matching."""

from __future__ import annotations

import re
from typing import Callable

from vnasim.scpi.types import ParsedCommand, Unhandled

# Handler signature: (cmd: ParsedCommand) -> str | None
Handler = Callable[[ParsedCommand], str | None]


def _extract_forms(keyword: str) -> tuple[str, str]:
    """Extract short form and full form from a SCPI keyword definition.

    The uppercase prefix is the mandatory abbreviation (short form).
    The full keyword uppercased is the full form.

    Examples:
        SENSe   -> ("SENS", "SENSE")
        FREQuency -> ("FREQ", "FREQUENCY")
        DATA    -> ("DATA", "DATA")
        CORRdata -> ("CORR", "CORRDATA")
    """
    short_end = 0
    for i, c in enumerate(keyword):
        if c.isupper() or c.isdigit() or c == '*':
            short_end = i + 1
        else:
            break
    else:
        # All characters consumed — entire keyword is the short form
        short_end = len(keyword)
    return keyword[:short_end].upper(), keyword.upper()


def _match_keyword(token: str, short: str, full: str) -> bool:
    """Check if *token* matches a SCPI keyword (case-insensitive).

    The token must be at least as long as the short form and at most
    as long as the full form, and must be a prefix of the full form.
    """
    t = token.upper()
    if len(t) < len(short) or len(t) > len(full):
        return False
    return full[:len(t)] == t


# Regex to split a token into keyword + optional numeric suffix
_SUFFIX_RE = re.compile(r'^([A-Za-z*]+)(\d+)?$')


class _ChildEntry:
    """A child node entry in the SCPI tree."""

    __slots__ = ('short', 'full', 'node')

    def __init__(self, short: str, full: str, node: SCPINode) -> None:
        self.short = short
        self.full = full
        self.node = node


class SCPINode:
    """A node in the SCPI command tree."""

    __slots__ = ('fixed_children', 'suffix_children',
                 'set_handler', 'query_handler')

    def __init__(self) -> None:
        self.fixed_children: list[_ChildEntry] = []
        self.suffix_children: list[_ChildEntry] = []
        self.set_handler: Handler | None = None
        self.query_handler: Handler | None = None

    def _find_or_create(
        self, short: str, full: str, has_suffix: bool,
    ) -> SCPINode:
        children = self.suffix_children if has_suffix else self.fixed_children
        for entry in children:
            if entry.short == short and entry.full == full:
                return entry.node
        node = SCPINode()
        children.append(_ChildEntry(short, full, node))
        return node

    def _find_child(self, token: str) -> tuple[SCPINode | None, int | None]:
        """Find a child matching *token*, returning (node, suffix_or_None)."""
        m = _SUFFIX_RE.match(token)
        if not m:
            return None, None
        keyword_part = m.group(1)
        suffix_str = m.group(2)

        if suffix_str is not None:
            # Token has an explicit numeric suffix — look in suffix children
            suffix = int(suffix_str)
            for entry in self.suffix_children:
                if _match_keyword(keyword_part, entry.short, entry.full):
                    return entry.node, suffix
            return None, None

        # No suffix — try fixed children first, then suffix children (default 1)
        for entry in self.fixed_children:
            if _match_keyword(keyword_part, entry.short, entry.full):
                return entry.node, None
        for entry in self.suffix_children:
            if _match_keyword(keyword_part, entry.short, entry.full):
                return entry.node, 1  # SCPI default suffix
        return None, None


class SCPITree:
    """SCPI command router with tree-based dispatch.

    Register commands with SCPI keyword definitions (mixed-case
    indicating the mandatory abbreviation).  Dispatch incoming
    command strings to the matching handler.

    Path syntax for :meth:`register`:
        ``:SENSe#:FREQuency:STARt``
    ``#`` after a keyword means it accepts a numeric suffix.
    """

    def __init__(self) -> None:
        self._root = SCPINode()
        self._common_set: dict[str, Handler] = {}
        self._common_query: dict[str, Handler] = {}

    def register(
        self,
        path: str,
        *,
        handler: Handler | None = None,
        set_handler: Handler | None = None,
        query_handler: Handler | None = None,
    ) -> None:
        """Register handlers for a SCPI command path.

        *handler* registers for both set and query.  Explicit
        *set_handler* / *query_handler* take precedence.
        """
        set_handler = set_handler or handler
        query_handler = query_handler or handler
        # IEEE 488.2 common commands (start with *)
        if path.startswith('*'):
            key = path.upper()
            if set_handler:
                self._common_set[key] = set_handler
            if query_handler:
                self._common_query[key] = query_handler
            return

        # Subsystem commands — walk/build tree
        parts = [p for p in path.split(':') if p]
        node = self._root
        for part in parts:
            has_suffix = part.endswith('#')
            keyword = part.rstrip('#')
            short, full = _extract_forms(keyword)
            node = node._find_or_create(short, full, has_suffix)

        if set_handler:
            node.set_handler = set_handler
        if query_handler:
            node.query_handler = query_handler

    def dispatch(self, command_str: str) -> str | None | Unhandled:
        """Parse and dispatch a SCPI command string.

        Returns:
            ``str`` — response for queries.
            ``None`` — command handled, no response (write commands).
            :class:`Unhandled` — command not recognised.
        """
        raw = command_str.strip()
        if not raw:
            return None

        # Check for query
        is_query = '?' in raw

        # Split command from arguments
        # For queries: ":SENS1:FREQ:DATA?" or ":SENS1:DATA:CORR? S21"
        # For sets: ":SENS1:FREQ:START 1e6"
        if is_query:
            # Remove trailing ? and split
            q_pos = raw.index('?')
            cmd_part = raw[:q_pos]
            # Arguments come after the ?
            args_part = raw[q_pos + 1:].strip()
        else:
            # Split at first space
            parts = raw.split(None, 1)
            cmd_part = parts[0]
            args_part = parts[1] if len(parts) > 1 else ''

        # IEEE 488.2 common commands
        if cmd_part.startswith('*'):
            key = cmd_part.upper()
            handlers = self._common_query if is_query else self._common_set
            handler = handlers.get(key)
            if handler is None:
                other = self._common_set if is_query else self._common_query
                if key in other:
                    direction = "query" if is_query else "set"
                    return Unhandled(raw, f"no {direction} handler registered")
                return Unhandled(raw, "unknown common command")
            parsed = ParsedCommand(
                raw=raw, is_query=is_query, arguments=args_part,
            )
            return handler(parsed)

        # Subsystem command — walk tree
        tokens = [t for t in cmd_part.split(':') if t]
        node = self._root
        suffixes: list[int] = []

        for token in tokens:
            child, suffix = node._find_child(token)
            if child is None:
                return Unhandled(raw, "no matching command path")
            node = child
            if suffix is not None:
                suffixes.append(suffix)

        parsed = ParsedCommand(
            raw=raw, is_query=is_query, arguments=args_part,
            suffixes=suffixes,
        )

        handler = node.query_handler if is_query else node.set_handler
        if handler is None:
            direction = "query" if is_query else "set"
            return Unhandled(raw, f"no {direction} handler registered")
        return handler(parsed)
