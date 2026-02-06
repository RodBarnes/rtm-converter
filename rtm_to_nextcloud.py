#!/usr/bin/env python3
"""
RTM to Nextcloud Tasks Converter

Converts Remember The Milk JSON exports to iCalendar format (.ics)
with VTODO components for import into Nextcloud Tasks.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


def escape_ical_text(text):
    """Escape text for iCalendar format."""
    if not text:
        return ''
    # Escape backslashes, commas, semicolons, and newlines
    text = str(text).replace('\\', '\\\\')
    text = text.replace(',', '\\,')
    text = text.replace(';', '\\;')
    text = text.replace('\n', '\\n')
    return text


def format_datetime(timestamp_ms, has_time=True):
    """Convert RTM timestamp (milliseconds) to iCalendar format."""
    if not timestamp_ms:
        return None
    
    dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
    
    if has_time:
        # Format: YYYYMMDDTHHMMSS
        return dt.strftime('%Y%m%dT%H%M%S')
    else:
        # Format: YYYYMMDD (date only)
        return dt.strftime('%Y%m%d')


def convert_priority(rtm_priority):
    """Convert RTM priority to iCalendar PRIORITY."""
    # RTM: P1 (highest), P2, P3 (lowest), or None
    # iCalendar: 1 (highest) to 9 (lowest), 0 = undefined
    priority_map = {
        'P1': 1,
        'P2': 5,
        'P3': 9
    }
    return priority_map.get(rtm_priority, 0)


def convert_recurrence(rtm_repeat):
    """Convert RTM repeat rule to iCalendar RRULE."""
    if not rtm_repeat:
        return None
    
    # RTM repeat format: "FREQ=WEEKLY;INTERVAL=1"
    # This is already in RRULE format
    return rtm_repeat


def convert_task_to_vtodo(task, lists, notes_by_series):
    """Convert a single RTM task to VTODO format."""
    lines = []
    lines.append('BEGIN:VTODO')
    
    # UID - unique identifier
    uid = f"rtm-{task['id']}"
    lines.append(f'UID:{uid}')
    
    # RELATED-TO - for subtasks (parent-child relationship)
    # RTM uses parent_id to indicate a task is a subtask
    if task.get('parent_id'):
        parent_uid = f"rtm-{task['parent_id']}"
        lines.append(f'RELATED-TO:{parent_uid}')
    
    # SUMMARY - task name
    summary = escape_ical_text(task.get('name', 'Untitled Task'))
    lines.append(f'SUMMARY:{summary}')
    
    # PRIORITY
    if task.get('priority'):
        priority = convert_priority(task['priority'])
        if priority > 0:
            lines.append(f'PRIORITY:{priority}')
    
    # Determine if we need time components for dates
    # iCalendar requires consistency: if one date has time, both should
    has_due_time = task.get('date_due_has_time', False)
    has_start_time = task.get('date_start_has_time', False)
    use_time = has_due_time or has_start_time  # If either has time, use time for both
    
    # DUE - due date
    if task.get('date_due'):
        due_date = format_datetime(task['date_due'], use_time)
        if due_date:
            if use_time:
                lines.append(f'DUE:{due_date}')
            else:
                lines.append(f'DUE;VALUE=DATE:{due_date}')
    
    # DTSTART - start date
    if task.get('date_start'):
        start_date = format_datetime(task['date_start'], use_time)
        if start_date:
            if use_time:
                lines.append(f'DTSTART:{start_date}')
            else:
                lines.append(f'DTSTART;VALUE=DATE:{start_date}')
    
    # STATUS and COMPLETED
    if task.get('date_completed'):
        lines.append('STATUS:COMPLETED')
        completed_date = format_datetime(task['date_completed'], True)
        if completed_date:
            lines.append(f'COMPLETED:{completed_date}')
    else:
        lines.append('STATUS:NEEDS-ACTION')
    
    # CREATED - creation date
    if task.get('date_created'):
        created_date = format_datetime(task['date_created'], True)
        if created_date:
            lines.append(f'CREATED:{created_date}')
    
    # LAST-MODIFIED - modification date
    if task.get('date_modified'):
        modified_date = format_datetime(task['date_modified'], True)
        if modified_date:
            lines.append(f'LAST-MODIFIED:{modified_date}')
    
    # RRULE - recurrence rule
    if task.get('repeat'):
        rrule = convert_recurrence(task['repeat'])
        if rrule:
            lines.append(f'RRULE:{rrule}')
    
    # URL - task URL
    if task.get('url'):
        url = escape_ical_text(task['url'])
        lines.append(f'URL:{url}')
    
    # CATEGORIES - tags and list name
    categories = []
    if task.get('tags'):
        categories.extend(task['tags'])
    
    # Add list name to categories
    list_id = str(task.get('list_id', ''))
    if list_id and list_id in lists:
        categories.append(lists[list_id])
    
    if categories:
        cats = ','.join(escape_ical_text(c) for c in categories)
        lines.append(f'CATEGORIES:{cats}')
    
    # DESCRIPTION - combine all notes for this task's series_id
    description_parts = []
    
    series_id = str(task.get('series_id', ''))
    if series_id and series_id in notes_by_series:
        for note in notes_by_series[series_id]:
            # RTM exports use 'content' field for note text
            note_text = note.get('content', '')
            if note_text:
                description_parts.append(note_text)
    
    if description_parts:
        description = escape_ical_text('\n\n'.join(description_parts))
        lines.append(f'DESCRIPTION:{description}')
    
    # Custom properties for RTM-specific data
    if task.get('postponed'):
        lines.append(f'X-RTM-POSTPONE-COUNT:{task["postponed"]}')
    
    lines.append('END:VTODO')
    return '\r\n'.join(lines)


def should_include_task(task, args, list_names):
    """Determine if a task should be included based on filter arguments."""
    
    # Filter by list inclusion/exclusion
    list_id = str(task.get('list_id', ''))
    list_name = list_names.get(list_id, '')
    
    if args.lists:
        if list_name not in args.lists:
            return False
    
    if args.exclude_lists:
        if list_name in args.exclude_lists:
            return False
    
    # Filter by completion status
    is_completed = bool(task.get('date_completed'))
    
    if args.incomplete_only and is_completed:
        return False
    
    # Filter by completion date
    if args.skip_completed_before and is_completed:
        completed_date = task.get('date_completed')
        if completed_date:
            completed_dt = datetime.fromtimestamp(completed_date / 1000.0)
            if completed_dt < args.skip_completed_before:
                return False
    
    return True


def parse_date(date_string):
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_string}. Use YYYY-MM-DD")


def main():
    parser = argparse.ArgumentParser(
        description='Convert Remember The Milk JSON export to Nextcloud Tasks format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  python rtm_to_nextcloud.py rtm_export.json
  
  # Only incomplete tasks
  python rtm_to_nextcloud.py rtm_export.json --incomplete-only
  
  # Skip old completed tasks
  python rtm_to_nextcloud.py rtm_export.json --skip-completed-before 2020-01-01
  
  # Convert specific lists only
  python rtm_to_nextcloud.py rtm_export.json --lists "Personal,Work,Shopping"
  
  # Exclude certain lists
  python rtm_to_nextcloud.py rtm_export.json --exclude-lists "Archive,Someday"
  
  # Combine filters
  python rtm_to_nextcloud.py rtm_export.json output/ --incomplete-only --lists "Personal,Work"
        """
    )
    
    parser.add_argument('input_file', type=Path,
                        help='RTM JSON export file')
    parser.add_argument('output_dir', type=Path, nargs='?',
                        help='Output directory (default: same as input file)')
    
    # Filter options
    filter_group = parser.add_argument_group('filter options')
    filter_group.add_argument('--incomplete-only', action='store_true',
                              help='Only convert incomplete tasks (skip all completed tasks)')
    filter_group.add_argument('--skip-completed-before', type=parse_date, metavar='DATE',
                              help='Skip completed tasks older than DATE (format: YYYY-MM-DD)')
    filter_group.add_argument('--lists', type=str, metavar='LIST1,LIST2',
                              help='Only convert specified lists (comma-separated)')
    filter_group.add_argument('--exclude-lists', type=str, metavar='LIST1,LIST2',
                              help='Exclude specified lists (comma-separated)')
    
    args = parser.parse_args()
    
    # Parse list arguments
    if args.lists:
        args.lists = [l.strip() for l in args.lists.split(',')]
    if args.exclude_lists:
        args.exclude_lists = [l.strip() for l in args.exclude_lists.split(',')]
    
    # Set output directory
    if args.output_dir is None:
        args.output_dir = args.input_file.parent
    
    # Create output directory if it doesn't exist
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Read and parse RTM export
        print(f'Reading RTM export from: {args.input_file}')
        with open(args.input_file, 'r', encoding='utf-8') as f:
            rtm_data = json.load(f)
        
        # Build list ID to name mapping
        lists = {}
        if rtm_data.get('lists'):
            for lst in rtm_data['lists']:
                lists[str(lst['id'])] = lst['name']
        
        # Show active filters
        if args.incomplete_only or args.skip_completed_before or args.lists or args.exclude_lists:
            print('\nActive filters:')
            if args.incomplete_only:
                print('  - Only incomplete tasks')
            if args.skip_completed_before:
                print(f'  - Skip completed tasks before {args.skip_completed_before.date()}')
            if args.lists:
                print(f'  - Only lists: {", ".join(args.lists)}')
            if args.exclude_lists:
                print(f'  - Exclude lists: {", ".join(args.exclude_lists)}')
        
        # Build notes mapping by series_id
        notes_by_series = {}
        if rtm_data.get('notes'):
            for note in rtm_data['notes']:
                series_id = str(note.get('series_id', ''))
                if series_id:
                    if series_id not in notes_by_series:
                        notes_by_series[series_id] = []
                    notes_by_series[series_id].append(note)
        
        # Filter and group tasks by list_id
        tasks_by_list = {}
        filtered_count = 0
        for task in rtm_data.get('tasks', []):
            if should_include_task(task, args, lists):
                list_id = str(task.get('list_id', ''))
                if list_id not in tasks_by_list:
                    tasks_by_list[list_id] = []
                tasks_by_list[list_id].append(task)
            else:
                filtered_count += 1
        
        if filtered_count > 0:
            print(f'\nFiltered out {filtered_count} tasks')
        
        # Convert each list to a separate ICS file
        print('\nConverting tasks to VCALENDAR/VTODO format...')
        total_tasks = 0
        total_incomplete = 0
        total_completed = 0
        files_created = []
        
        for list_id, tasks in tasks_by_list.items():
            list_name = lists.get(list_id, f'List-{list_id}')
            
            # Sanitize filename (remove invalid characters)
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in list_name)
            output_file = args.output_dir / f'{safe_name}.ics'
            
            # Create VCALENDAR for this list
            lines = []
            lines.append('BEGIN:VCALENDAR')
            lines.append('VERSION:2.0')
            lines.append('PRODID:-//RTM to Nextcloud Converter//EN')
            lines.append('CALSCALE:GREGORIAN')
            lines.append(f'X-WR-CALNAME:{escape_ical_text(list_name)}')
            
            # Convert each task in this list
            for task in tasks:
                lines.append(convert_task_to_vtodo(task, lists, notes_by_series))
            
            lines.append('END:VCALENDAR')
            ics_content = '\r\n'.join(lines)
            
            # Write output file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(ics_content)
            
            # Count stats
            incomplete = sum(1 for t in tasks if not t.get('date_completed'))
            completed = sum(1 for t in tasks if t.get('date_completed'))
            
            total_tasks += len(tasks)
            total_incomplete += incomplete
            total_completed += completed
            files_created.append((output_file.name, len(tasks), incomplete, completed))
            
            print(f'  {list_name}: {len(tasks)} tasks -> {output_file.name}')
        
        # Print summary
        print()
        print('✓ Conversion complete!')
        print(f'  Total tasks: {total_tasks}')
        print(f'  - Incomplete: {total_incomplete}')
        print(f'  - Completed: {total_completed}')
        print(f'  Files created: {len(files_created)}')
        print()
        print(f'Output directory: {args.output_dir}')
        print()
        print('Import these files into Nextcloud Tasks via:')
        print('  Calendar app → Settings & Import → Import Calendar')
        print('  (Import each .ics file separately to create separate task lists)')
        
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
