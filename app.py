# app.py
from textual.app import App
from ui.table_view import LeaderboardScreen


class LeaderboardApp(App):
    CSS = """
    #status {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text-muted;
    }
    DataTable {
        height: 1fr;
    }
    """

    def on_mount(self) -> None:
        self.push_screen(LeaderboardScreen())


if __name__ == "__main__":
    LeaderboardApp().run()
