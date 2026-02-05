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
- ✅ Notes (converted to DESCRIPTION)
- ✅ Tags (converted to CATEGORIES)
- ✅ List names (added to CATEGORIES)
- ✅ Subtasks (converted to RELATED-TO for parent-child relationships)
- ✅ Metadata (postpone count, source)

## Usage

### Python Version (Recommended)

```bash
# Basic usage
python3 rtm_to_nextcloud.py rtm_export.json

# Specify output file
python3 rtm_to_nextcloud.py rtm_export.json my_tasks.ics
```

### Dart Version

```bash
# Basic usage
dart rtm_to_nextcloud.dart rtm_export.json

# Specify output file
dart rtm_to_nextcloud.dart rtm_export.json my_tasks.ics
```

## Exporting from RTM

1. Log into Remember The Milk
2. Go to Settings → Account
3. Click "Export data"
4. Download the JSON export file

## Importing to Nextcloud

1. Open Nextcloud Calendar app
2. Click **Settings & Import** (bottom left)
3. Click **+ Import Calendar**
4. Select the generated `.ics` file
5. The tasks will appear in your Tasks app

## Example Output

```
✓ Conversion complete!
  Total tasks: 84
  - Incomplete: 50
  - Completed: 34

Import this file into Nextcloud Tasks via:
  Calendar app → Settings & Import → Import Calendar
```

## Data Mapping

| RTM Field | Nextcloud (VTODO) Field | Notes |
|-----------|------------------------|-------|
| `name` | `SUMMARY` | Task title |
| `id` | `UID` | Unique identifier (prefixed with "rtm-") |
| `parent_id` | `RELATED-TO` | Creates parent-child subtask relationships |
| `series_id` | Used to match notes | Links tasks to their notes in the notes array |
| `priority` | `PRIORITY` | P1→1, P2→5, P3→9 |
| `date_due` | `DUE` | With or without time |
| `date_start` | `DTSTART` | With or without time |
| `date_completed` | `COMPLETED`, `STATUS` | Sets STATUS:COMPLETED |
| `date_created` | `CREATED` | ISO 8601 timestamp |
| `date_modified` | `LAST-MODIFIED` | ISO 8601 timestamp |
| `repeat` | `RRULE` | Recurrence rule |
| `url` | `URL` | Task URL |
| `tags` | `CATEGORIES` | Tags as comma-separated list |
| `list_id` | `CATEGORIES` | List name added to categories |
| `notes` | `DESCRIPTION` | All notes combined |

## Requirements

### Python Version
- Python 3.6 or higher
- No additional dependencies (uses only standard library)

### Dart Version
- Dart SDK 2.12 or higher
- No additional dependencies (uses only dart:core)

## Testing

The tool has been tested with:
- Sample RTM export containing 84 tasks
- Tasks with various priorities
- Recurring tasks
- Tasks with notes
- Completed and incomplete tasks
- Tasks with URLs
- Tasks with due dates (with and without times)

## Limitations

- **Contacts**: RTM contact assignments are not preserved (Nextcloud Tasks doesn't have a direct equivalent).
- **Time estimates**: RTM time estimates are not converted.
- **Locations**: RTM location data is not converted.

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
