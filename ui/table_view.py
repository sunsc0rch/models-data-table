import asyncio
import json
import pyperclip
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label
from textual import work

import core.cache as cache
import core.merger as merger
from core.models import ModelRecord
from scrapers import SCRAPER_REGISTRY

COLUMNS = [
    ("Model", "name"),
    ("Provider", "provider"),
    ("Params (B)", "params_b"),
    ("Context (K)", "context_k"),
    ("SWE-bench %", "swe_bench_pct"),
    ("Free via", "free_providers"),
]


class LeaderboardScreen(Screen):
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("f", "toggle_free", "Free only"),
        Binding("enter", "copy_snippet", "Copy snippet"),
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

    def _render_table(self) -> None:
        records = self._records
        if self._free_only:
            records = [r for r in records if r.free_providers]
        records = sorted(
            records,
            key=lambda r: (getattr(r, self._sort_col) is None,
                           getattr(r, self._sort_col) or 0),
            reverse=not self._sort_asc,
        )
        table = self.query_one(DataTable)
        table.clear()
        for r in records:
            params = f"{r.params_b:.0f}B" if r.params_b is not None else "—"
            context = f"{r.context_k}K" if r.context_k is not None else "—"
            swe = f"{r.swe_bench_pct:.1f}%" if r.swe_bench_pct is not None else "—"
            free = ", ".join(r.free_providers) if r.free_providers else "—"
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

    def action_copy_snippet(self) -> None:
        table = self.query_one(DataTable)
        row_idx = table.cursor_row
        visible = self._records
        if self._free_only:
            visible = [r for r in visible if r.free_providers]
        visible = sorted(
            visible,
            key=lambda r: (getattr(r, self._sort_col) is None,
                           getattr(r, self._sort_col) or 0),
            reverse=not self._sort_asc,
        )
        if row_idx >= len(visible):
            return
        record = visible[row_idx]
        snippet = _build_snippet(record)
        status = self.query_one("#status", Label)
        try:
            pyperclip.copy(snippet)
            status.update(f"Copied snippet for [bold]{record.name}[/bold]")
        except pyperclip.PyperclipException:
            status.update(f"Clipboard unavailable. Snippet: {snippet}")

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        status = self.query_one("#status", Label)
        status.update("Refreshing…")
        results = await asyncio.gather(*[s.fetch() for s in SCRAPER_REGISTRY])
        errors = []
        record_lists = []
        for scraper, (records, err) in zip(SCRAPER_REGISTRY, results):
            record_lists.append(records)
            if err:
                errors.append(f"⚠ {scraper.name}: {type(err).__name__}")
        merged = merger.merge(record_lists)
        cache.write(merged)
        self._records = cache.read()
        self._render_table()
        msg = " | ".join(errors) if errors else f"Updated — {len(merged)} models"
        status.update(msg)


def _build_snippet(record: ModelRecord) -> str:
    model_id = record.openrouter_id or f"{record.name}:free"
    display_name = record.openrouter_name or record.name
    context = (record.context_k or 128) * 1000
    output = record.output_tokens or 8192
    body = json.dumps({"name": display_name, "limit": {"context": context, "output": output}}, indent=2)
    return f'"{model_id}": {body}'
