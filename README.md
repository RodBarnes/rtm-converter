# RTM to Nextcloud Tasks Converter

Convert Remember The Milk (RTM) task exports to Nextcloud Tasks format.

## Overview

This tool converts RTM JSON exports to iCalendar format (`.ics` files) with VTODO components, which can be imported into Nextcloud Tasks.

## Format Verification

✅ **Confirmed**: Nextcloud Tasks uses the iCalendar format with VTODO components (RFC 5545)

The output format is:
```
BEGIN:VCALENDAR
  VERSION:2.0
  PRODID:-//RTM to Nextcloud Converter//EN
  BEGIN:VTODO
    UID:rtm-[task-id]
    SUMMARY:[task name]
    [additional properties...]
  END:VTODO
  [more tasks...]
END:VCALENDAR
```

## Features

The converter handles:

### Task Properties
- ✅ Task name (SUMMARY)
- ✅ Priority (P1 → 1, P2 → 5, P3 → 9)
- ✅ Due date (with/without time)
- ✅ Start date (with/without time)
- ✅ Completion status and date
- ✅ Creation and modification timestamps
- ✅ Recurrence rules (RRULE)
- ✅ Task URLs
- ✅ Unique identifiers (UID)

### Additional Data
- ✅ Notes (converted to DESCRIPTION, matched by series_id)
- ✅ Tags (converted to CATEGORIES)
- ✅ List names (added to CATEGORIES)
- ✅ Subtasks (converted to RELATED-TO for parent-child relationships)
- ✅ Postpone count (converted to X-RTM-POSTPONE-COUNT)

## Usage

**Note:** RTM export files are typically named like `rememberthemilk_export_2026-02-05T20_17_19.767Z.json`. Replace `<rtm-export.json>` in the examples below with your actual export filename.

```bash
# Basic usage - creates separate .ics files for each list in the same directory as the input
python rtm_to_nextcloud.py <rtm-export.json>

# Specify output directory
python rtm_to_nextcloud.py <rtm-export.json> /path/to/output/directory

# Only convert incomplete tasks (skip all completed tasks)
python rtm_to_nextcloud.py <rtm-export.json> --incomplete-only

# Skip old completed tasks (keep recent completions)
python rtm_to_nextcloud.py <rtm-export.json> --skip-completed-before 2020-01-01

# Convert only specific lists
python rtm_to_nextcloud.py <rtm-export.json> --lists "Personal,Work,Shopping"

# Exclude certain lists
python rtm_to_nextcloud.py <rtm-export.json> --exclude-lists "Archive,Someday"

# Combine multiple filters
python rtm_to_nextcloud.py <rtm-export.json> output/ --incomplete-only --lists "Personal,Work"
```

The converter creates a separate `.ics` file for each RTM list, allowing you to import them as separate task lists in Nextcloud.

### Filter Options

- `--incomplete-only` - Only convert incomplete tasks, skip all completed tasks
- `--skip-completed-before DATE` - Skip completed tasks older than the specified date (format: YYYY-MM-DD)
- `--lists LIST1,LIST2` - Only convert the specified lists (comma-separated list names)
- `--exclude-lists LIST1,LIST2` - Exclude the specified lists (comma-separated list names)

Filters can be combined to create exactly the subset of tasks you want to import.

## Exporting from RTM

1. Log into Remember The Milk
2. Go to Settings → Account
3. Click "Export data"
4. Download the JSON export file

## Importing to Nextcloud

1. Open Nextcloud Calendar app
2. Click **Settings & Import** (bottom left)
3. Click **+ Import Calendar**
4. Import each `.ics` file separately - each will create a separate task list
5. The tasks will appear in your Tasks app organized by list

## Example Output

```
✓ Conversion complete!
  Total tasks: 87
  - Incomplete: 51
  - Completed: 36
  Files created: 5

Output directory: ./output

Import these files into Nextcloud Tasks via:
  Calendar app → Settings & Import → Import Calendar
  (Import each .ics file separately to create separate task lists)
```

Each RTM list becomes a separate `.ics` file:
- `Personal.ics`
- `Inbox.ics`
- `Technology.ics`
- `House.ics`
- etc.

## Data Mapping

| RTM Field | Nextcloud (VTODO) Field | Notes |
|-----------|------------------------|-------|
| `name` | `SUMMARY` | Task title |
| `id` | `UID` | Unique identifier (prefixed with "rtm-") |
| `parent_id` | `RELATED-TO` | Creates parent-child subtask relationships |
| `series_id` | Used to match notes | Links tasks to their notes in the notes array |
| `priority` | `PRIORITY` | P1→1, P2→5, P3→9 |
| `date_due` | `DUE` | With or without time based on date_due_has_time |
| `date_due_has_time` | `DUE` format | True: includes time, False: date only (VALUE=DATE) |
| `date_start` | `DTSTART` | With or without time based on date_start_has_time |
| `date_start_has_time` | `DTSTART` format | True: includes time, False: date only (VALUE=DATE) |
| `date_completed` | `COMPLETED`, `STATUS` | Sets STATUS:COMPLETED |
| `date_created` | `CREATED` | ISO 8601 timestamp |
| `date_modified` | `LAST-MODIFIED` | ISO 8601 timestamp |
| `repeat` | `RRULE` | Recurrence rule |
| `url` | `URL` | Task URL |
| `tags` | `CATEGORIES` | Tags as comma-separated list |
| `list_id` | `CATEGORIES` | List name added to categories |
| `notes` (array) | `DESCRIPTION` | Notes matched by series_id, combined with blank lines |
| `postponed` | `X-RTM-POSTPONE-COUNT` | Number of times task was postponed |

**Important Note on Date/Time Handling:** 
iCalendar requires consistency in date formatting. If either `date_due_has_time` or `date_start_has_time` is True, both dates will be formatted with time components to ensure valid iCalendar format. This differs from RTM which allows mixed formats (e.g., start with time, due as all-day).

## Requirements

- Python 3.6 or higher
- No additional dependencies (uses only standard library)

## Testing

The tool has been tested with:
- Sample RTM export containing 86+ tasks designed to exercise all RTM features
- Tasks with various priorities (P1, P2, P3, and no priority)
- Recurring tasks with different frequencies
- Tasks with notes (matched via series_id)
- Completed and incomplete tasks
- Tasks with URLs
- Tasks with due dates (with and without times)
- Tasks with start dates (with and without times)
- Mixed date/time formats (start with time, due without time)
- Subtasks and parent-child relationships
- Tasks with postpone counts
- Tasks spanning 15+ years of data

## Limitations

- **Contacts**: RTM contact assignments are not preserved (Nextcloud Tasks doesn't have a direct equivalent).
- **Time estimates**: RTM time estimates are not converted.
- **Locations**: RTM location data is not converted.
- **Source field**: The `source` field (indicating where task was created) is not converted as it provides no value after migration.
- **repeat_every**: This boolean flag is redundant (RRULE contains all recurrence information) and is not converted.

## Troubleshooting

### Import fails in Nextcloud
- Ensure you're using the Calendar app's import feature, not the Tasks app directly
- Try importing a smaller subset of tasks first
- Check Nextcloud logs for specific error messages

### Tasks appear with wrong dates
- Verify your timezone settings in Nextcloud match your expectations
- RTM stores times in milliseconds since epoch; ensure your export is recent

### Notes not showing
- Notes are combined into the DESCRIPTION field
- Check if your Nextcloud Tasks app version supports task descriptions

## License

This tool is provided as-is for personal use. Feel free to modify and distribute.

## Author

Created as a migration tool for users moving from Remember The Milk to Nextcloud Tasks.
