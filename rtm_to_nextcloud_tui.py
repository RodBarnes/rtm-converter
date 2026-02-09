#!/usr/bin/env python3
"""
RTM to Nextcloud Tasks Converter - TUI Version

Interactive text-based UI for converting Remember The Milk exports
to Nextcloud Tasks format.
"""

# pylint: disable=broad-except

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Button, Static, Checkbox, Input, Label
from textual.binding import Binding

# Import conversion functions from the CLI version
from rtm_to_nextcloud import (
    escape_ical_text,
    convert_task_to_vtodo,
    should_include_task
)


class ListItem(Container):
    """A single list item with checkbox and task count."""

    def __init__(self, list_id:
      str, list_name: str, task_count: int, incomplete: int, completed: int):
        super().__init__()
        self.list_id = list_id
        self.list_name = list_name
        self.task_count = task_count
        self.incomplete = incomplete
        self.completed = completed
        self.enabled = True

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Checkbox(f"{self.list_name}", value=True, id=f"list_{self.list_id}")
            yield Label(f"({self.task_count} tasks: {self.incomplete} incomplete, {self.completed} completed)")


class RTMConverterApp(App):
    """A Textual app to convert RTM exports."""

    CSS = """
    Screen {
        background: $surface;
    }

    #title {
        dock: top;
        height: 3;
        content-align: center middle;
        background: $primary;
        color: $text;
        text-style: bold;
    }

    #main-container {
        height: 100%;
        padding: 1 2;
    }

    .section {
        border: solid $primary;
        height: auto;
        margin: 1 0;
        padding: 1;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #lists-container {
        height: 20;
        border: solid $primary;
        padding: 1;
    }

    #filters-container {
        height: auto;
        margin-top: 1;
    }

    #button-container {
        dock: bottom;
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    Input {
        width: 30;
    }

    .info {
        color: $text-muted;
        margin-left: 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "convert", "Convert"),
    ]

    def __init__(self, input_file: Path, output_dir: Optional[Path] = None):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir if output_dir else input_file.parent
        self.rtm_data = None
        self.lists = {}
        self.list_items = []
        self.load_data()

    def load_data(self):
        """Load and parse the RTM export file."""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                self.rtm_data = json.load(f)

            # Build list mapping
            if self.rtm_data.get('lists'):
                for lst in self.rtm_data['lists']:
                    self.lists[str(lst['id'])] = lst['name']

            # Count tasks per list
            self.list_task_counts = {}
            for task in self.rtm_data.get('tasks', []):
                list_id = str(task.get('list_id', ''))
                if list_id not in self.list_task_counts:
                    self.list_task_counts[list_id] = {
                        'total': 0,
                        'incomplete': 0,
                        'completed': 0
                    }
                self.list_task_counts[list_id]['total'] += 1
                if task.get('date_completed'):
                    self.list_task_counts[list_id]['completed'] += 1
                else:
                    self.list_task_counts[list_id]['incomplete'] += 1

        except Exception as e:
            self.rtm_data = None
            self.error_message = str(e)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with Container(id="main-container"):
            yield Static("RTM to Nextcloud Tasks Converter", id="title")

            # File info
            with Container(classes="section"):
                yield Label("Input file:", classes="section-title")
                yield Label(f"  {self.input_file.name}", classes="info")
                yield Label("Output directory:", classes="section-title")
                yield Label(f"  {self.output_dir.resolve()}", classes="info")

            # Lists
            with Container(classes="section"):
                yield Label("Select lists to convert:", classes="section-title")
                with ScrollableContainer(id="lists-container"):
                    if self.rtm_data:
                        for list_id, list_name in sorted(self.lists.items(), key=lambda x: x[1]):
                            if list_id in self.list_task_counts:
                                counts = self.list_task_counts[list_id]
                                yield ListItem(
                                    list_id,
                                    list_name,
                                    counts['total'],
                                    counts['incomplete'],
                                    counts['completed']
                                )

            # Filters
            with Container(id="filters-container", classes="section"):
                yield Label("Filters:", classes="section-title")
                yield Checkbox("Incomplete tasks only", id="incomplete-only")
                with Horizontal():
                    yield Label("Skip completed before:")
                    yield Input(placeholder="YYYY-MM-DD", id="skip-date")

            # Buttons
            with Horizontal(id="button-container"):
                yield Button("Convert", variant="primary", id="convert-btn")
                yield Button("Quit", variant="default", id="quit-btn")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "convert-btn":
            self.action_convert()
        elif event.button.id == "quit-btn":
            self.exit()

    def action_convert(self) -> None:
        """Perform the conversion."""
        if not self.rtm_data:
            self.notify("No data loaded!", severity="error")
            return

        try:
            # Gather selected lists
            selected_lists = []
            for widget in self.query(ListItem):
                checkbox = self.query_one(f"#list_{widget.list_id}", Checkbox)
                if checkbox.value:
                    selected_lists.append(widget.list_name)

            if not selected_lists:
                self.notify("No lists selected!", severity="warning")
                return

            # Gather filter options
            incomplete_only = self.query_one("#incomplete-only", Checkbox).value
            skip_date_str = self.query_one("#skip-date", Input).value.strip()

            skip_date = None
            if skip_date_str:
                try:
                    skip_date = datetime.strptime(skip_date_str, '%Y-%m-%d')
                except ValueError:
                    self.notify("Invalid date format! Use YYYY-MM-DD", severity="error")
                    return

            # Create args object to match CLI version
            class Args:
                """Arguments object to match CLI version's argparse Namespace."""
                lists: list[str]
                exclude_lists: Optional[list[str]]
                incomplete_only: bool
                skip_completed_before: Optional[datetime]
                output_dir: Path

            args = Args()
            args.lists = selected_lists
            args.exclude_lists = None
            args.incomplete_only = incomplete_only
            args.skip_completed_before = skip_date
            args.output_dir = self.output_dir

            # Build notes mapping
            notes_by_series = {}
            if self.rtm_data.get('notes'):
                for note in self.rtm_data['notes']:
                    series_id = str(note.get('series_id', ''))
                    if series_id:
                        if series_id not in notes_by_series:
                            notes_by_series[series_id] = []
                        notes_by_series[series_id].append(note)

            # Filter and group tasks by list
            tasks_by_list = {}
            filtered_count = 0
            for task in self.rtm_data.get('tasks', []):
                if should_include_task(task, args, self.lists):
                    list_id = str(task.get('list_id', ''))
                    if list_id not in tasks_by_list:
                        tasks_by_list[list_id] = []
                    tasks_by_list[list_id].append(task)
                else:
                    filtered_count += 1

            # Convert each list
            total_tasks = 0
            files_created = 0

            for list_id, tasks in tasks_by_list.items():
                list_name = self.lists.get(list_id, f'List-{list_id}')

                # Sanitize filename
                safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in list_name)
                output_file = self.output_dir / f'{safe_name}.ics'

                # Create VCALENDAR
                lines = []
                lines.append('BEGIN:VCALENDAR')
                lines.append('VERSION:2.0')
                lines.append('PRODID:-//RTM to Nextcloud Converter//EN')
                lines.append('CALSCALE:GREGORIAN')
                lines.append(f'X-WR-CALNAME:{escape_ical_text(list_name)}')

                for task in tasks:
                    lines.append(convert_task_to_vtodo(task, self.lists, notes_by_series))

                lines.append('END:VCALENDAR')
                ics_content = '\r\n'.join(lines)

                # Write file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(ics_content)

                total_tasks += len(tasks)
                files_created += 1

            # Show success message
            message = "✓ Conversion complete!\n"
            message += f"  Total tasks: {total_tasks}\n"
            if filtered_count > 0:
                message += f"  Filtered out: {filtered_count}\n"
            message += f"  Files created: {files_created}\n"
            message += f"\nOutput: {self.output_dir}"

            self.notify(message, severity="information", timeout=10)

        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error")

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def main():
    """Run the TUI application."""
    if len(sys.argv) < 2:
        print("Usage: python rtm_to_nextcloud_tui.py <rtm-export.json> [output_directory]")
        print()
        print("Interactive TUI for converting RTM exports to Nextcloud Tasks")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    # Optional output directory argument
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    app = RTMConverterApp(input_file, output_dir)
    app.run()


if __name__ == '__main__':
    main()
