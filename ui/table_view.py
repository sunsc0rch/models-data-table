import asyncio
import json
import pyperclip
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label
from textual import work

import core.cache as cache
import core.fcm_updater as fcm_updater
import core.merger as merger
import core.static_data as static_data
from core.models import ModelRecord
from core.opencode_providers import resolve_api_provider, resolve_model_id
from scrapers import SCRAPER_REGISTRY

COLUMNS = [
    ("Model", "name"),
    ("Provider", "provider"),
    ("Params (B)", "params_b"),
    ("Context (K)", "context_k"),
    ("Coding", "swe_bench_pct"),
    ("Free via", "free_providers"),
]


class LeaderboardScreen(Screen):
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("f", "toggle_free", "Free only"),
        Binding("enter", "copy_snippet", "Copy + comma"),
        Binding("shift+enter", "copy_snippet_last", "Copy (no comma)"),
        Binding("q", "app.quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self._records: list[ModelRecord] = []
        self._free_only = False
        self._sort_col: str = "swe_bench_pct"
        self._sort_asc = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("", id="status")
        yield DataTable(cursor_type="row", id="table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for label, _ in COLUMNS:
            table.add_column(label, key=label)
        self._records = cache.read()
        if not self._records:
            self.query_one("#status", Label).update(
                "No data — press [bold]R[/bold] to refresh"
            )
        else:
            self._render_table()

    def _sort_key(self, r: ModelRecord) -> tuple:
        val = getattr(r, self._sort_col)
        if self._sort_col == "swe_bench_pct":
            val = _coding_pct(r)
        if val is None:
            return (1, "")
        if isinstance(val, list):
            return (0, ", ".join(val))
        return (0, val)

    def _visible_sorted_records(self) -> list[ModelRecord]:
        records = [r for r in self._records if not self._free_only or r.free_providers]
        return sorted(records, key=self._sort_key, reverse=not self._sort_asc)

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for r in self._visible_sorted_records():
            params = f"{r.params_b:.0f}B" if r.params_b is not None else "—"
            context = f"{r.context_k}K" if r.context_k is not None else "—"
            score = _coding_pct(r)
            swe = f"{score:.1f}%" if score is not None else "—"
            free = _format_free_providers(r.free_providers)
            table.add_row(r.name, r.provider or "—", params, context, swe, free)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        col_map = {label: field for label, field in COLUMNS}
        field = col_map.get(str(event.label))
        if not field:
            return
        if self._sort_col == field:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = field
            self._sort_asc = False
        self._render_table()

    def action_toggle_free(self) -> None:
        self._free_only = not self._free_only
        status = self.query_one("#status", Label)
        status.update("[bold]Showing free models only[/bold]" if self._free_only else "")
        self._render_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._do_copy(trailing_comma=True)

    def action_copy_snippet(self) -> None:
        self._do_copy(trailing_comma=True)

    def action_copy_snippet_last(self) -> None:
        self._do_copy(trailing_comma=False)

    def _do_copy(self, *, trailing_comma: bool) -> None:
        table = self.query_one(DataTable)
        visible = self._visible_sorted_records()
        row_idx = table.cursor_row
        if row_idx < 0 or row_idx >= len(visible):
            return
        record = visible[row_idx]
        api_provider = resolve_api_provider(record)
        snippet, id_source = _build_snippet(
            record, api_provider=api_provider, trailing_comma=trailing_comma,
        )
        status = self.query_one("#status", Label)
        if api_provider:
            where = f"provider.{api_provider}.models"
        else:
            where = "provider.<unknown>.models"
        msg = f"Copied [bold]{record.name}[/bold] → [bold]{where}[/bold]"
        if api_provider is None:
            msg += "  ⚠ provider unknown — check opencode.json"
        elif id_source == "fallback":
            msg += (
                f"  ⚠ no exact API ID for {api_provider} — "
                f"placeholder used, verify the ID"
            )
        try:
            pyperclip.copy(snippet)
            status.update(msg)
        except pyperclip.PyperclipException:
            status.update(f"Clipboard unavailable. Snippet: {snippet}")

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        status = self.query_one("#status", Label)
        status.update("Refreshing…")
        all_tasks = [*[s.fetch() for s in SCRAPER_REGISTRY], fcm_updater.refresh()]
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
        scraper_results = all_results[: len(SCRAPER_REGISTRY)]
        fcm_result = all_results[-1]

        errors = []
        record_lists = []
        for scraper, result in zip(SCRAPER_REGISTRY, scraper_results):
            if isinstance(result, BaseException):
                record_lists.append([])
                errors.append(f"⚠ {scraper.name}: {type(result).__name__}")
            else:
                records, err = result
                record_lists.append(records)
                if err:
                    errors.append(f"⚠ {scraper.name}: {type(err).__name__}")

        if isinstance(fcm_result, BaseException) or (isinstance(fcm_result, tuple) and fcm_result[1]):
            err = fcm_result if isinstance(fcm_result, BaseException) else fcm_result[1]
            errors.append(f"⚠ fcm: {type(err).__name__}")

        merged = static_data.enrich(merger.merge(record_lists))
        cache.write(merged)
        self._records = cache.read()
        self._render_table()
        msg = " | ".join(errors) if errors else f"Updated — {len(merged)} models"
        status.update(msg)


_AA_CODING_MAX = 60.0  # empirical ceiling of AA coding index scale


def _coding_pct(record: ModelRecord) -> float | None:
    """Return a unified 0-100 coding % for any record.

    SWE-bench and Aider scores are already in %; AA coding index (0-60 scale)
    is normalised by dividing by the empirical maximum of 60.
    """
    if record.swe_bench_pct is not None:
        return record.swe_bench_pct
    if record.coding_index is not None:
        return round(record.coding_index / _AA_CODING_MAX * 100, 1)
    return None


def _format_free_providers(providers: list[str]) -> str:
    if not providers:
        return "—"
    if len(providers) <= 3:
        return ", ".join(providers)
    return f"{', '.join(providers[:3])} +{len(providers) - 3}"


def _build_snippet(
    record: ModelRecord,
    *,
    api_provider: str | None = None,
    indent: int = 8,
    trailing_comma: bool = True,
) -> tuple[str, str]:
    """Build a JSON snippet that slots into ``provider.<key>.models``.

    Default 8-space indent matches the layout used in
    ``~/.config/opencode/opencode.json``. Trailing comma on by default
    (typical for inserting mid-list); pass ``trailing_comma=False`` for
    the final entry.

    Returns ``(snippet, id_source)`` where ``id_source`` is one of
    ``"model_ids"``, ``"openrouter_id"``, or ``"fallback"`` — see
    ``core.opencode_providers.resolve_model_id``.
    """
    model_id, id_source = resolve_model_id(record, api_provider)
    display_name = record.openrouter_name or record.name
    context = (record.context_k or 128) * 1000
    output = record.output_tokens or 8192
    lines = json.dumps(
        {"name": display_name, "limit": {"context": context, "output": output}},
        indent=2,
    ).split("\n")
    # First line is the opening "{" — keep it on the key line.
    # All other lines (already at 0/2/4 spaces from json.dumps) get
    # shifted right by `indent` so they align under the key.
    rest = "\n".join(" " * indent + line for line in lines[1:])
    head = f'{" " * indent}"{model_id}": {lines[0]}'
    body = f"{head}\n{rest}" if rest else head
    suffix = "," if trailing_comma else ""
    return body + suffix, id_source
