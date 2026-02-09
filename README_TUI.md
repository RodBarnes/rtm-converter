# RTM to Nextcloud Tasks Converter - TUI Version

Interactive text-based user interface for converting Remember The Milk exports to Nextcloud Tasks.

## Installation

The TUI version requires the `textual` library:

```bash
pip install textual --break-system-packages
```

## Usage

```bash
python rtm_to_nextcloud_tui.py <rtm-export.json>
```

This will launch an interactive interface where you can:
- Select which lists to convert (checkboxes)
- Filter for incomplete tasks only
- Skip completed tasks before a specific date
- See task counts for each list
- Convert with a button click

## Features

- **Visual list selection**: Check/uncheck lists you want to convert
- **Task counts**: See total, incomplete, and completed task counts per list
- **Filter options**: 
  - Incomplete tasks only checkbox
  - Skip completed before date field (YYYY-MM-DD format)
- **Keyboard shortcuts**:
  - `c` - Convert
  - `q` - Quit
  - `Tab` - Navigate between elements
  - `Space` - Toggle checkboxes

## Why use the TUI?

- **Easier to use**: No need to remember command-line arguments
- **Visual feedback**: See all your lists and task counts at once
- **Interactive**: Check/uncheck lists and see what you're converting
- **Less error-prone**: Date validation and clear options

## CLI version still available

The command-line version (`rtm_to_nextcloud.py`) is still available for:
- Scripting and automation
- Running on systems without textual
- Command-line preferences

Both versions produce identical output files.
