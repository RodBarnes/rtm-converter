#!/usr/bin/env python3
"""
RTM to Nextcloud Tasks Converter

Converts Remember The Milk JSON exports to iCalendar format (.ics)
with VTODO components for import into Nextcloud Tasks.
"""

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
    
    # DUE - due date
    if task.get('date_due'):
        has_due_time = task.get('has_due_time', False)
        due_date = format_datetime(task['date_due'], has_due_time)
        if due_date:
            if has_due_time:
                lines.append(f'DUE:{due_date}')
            else:
                lines.append(f'DUE;VALUE=DATE:{due_date}')
    
    # DTSTART - start date
    if task.get('date_start'):
        has_start_time = task.get('has_start_time', False)
        start_date = format_datetime(task['date_start'], has_start_time)
        if start_date:
            if has_start_time:
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
    if task.get('postpone_count'):
        lines.append(f'X-RTM-POSTPONE-COUNT:{task["postpone_count"]}')
    
    if task.get('source'):
        source = escape_ical_text(task['source'])
        lines.append(f'X-RTM-SOURCE:{source}')
    
    lines.append('END:VTODO')
    return '\r\n'.join(lines)


def convert_rtm_to_ics(rtm_data):
    """Convert RTM export to VCALENDAR format."""
    lines = []
    
    # VCALENDAR header
    lines.append('BEGIN:VCALENDAR')
    lines.append('VERSION:2.0')
    lines.append('PRODID:-//RTM to Nextcloud Converter//EN')
    lines.append('CALSCALE:GREGORIAN')
    lines.append('X-WR-CALNAME:RTM Tasks')
    
    # Build list ID to name mapping
    lists = {}
    if rtm_data.get('lists'):
        for lst in rtm_data['lists']:
            lists[str(lst['id'])] = lst['name']
    
    # Build notes mapping by series_id
    notes_by_series = {}
    if rtm_data.get('notes'):
        for note in rtm_data['notes']:
            series_id = str(note.get('series_id', ''))
            if series_id:
                if series_id not in notes_by_series:
                    notes_by_series[series_id] = []
                notes_by_series[series_id].append(note)
    
    # Convert each task to VTODO
    tasks = rtm_data.get('tasks', [])
    for task in tasks:
        lines.append(convert_task_to_vtodo(task, lists, notes_by_series))
    
    # VCALENDAR footer
    lines.append('END:VCALENDAR')
    
    return '\r\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 rtm_to_nextcloud.py <rtm_export.json> [output_file.ics]')
        print()
        print('Converts Remember The Milk export to Nextcloud Tasks format (VCALENDAR/VTODO)')
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else input_file.with_suffix('.ics')
    
    try:
        # Read and parse RTM export
        print(f'Reading RTM export from: {input_file}')
        with open(input_file, 'r', encoding='utf-8') as f:
            rtm_data = json.load(f)
        
        # Convert to VCALENDAR format
        print('Converting tasks to VCALENDAR/VTODO format...')
        ics_content = convert_rtm_to_ics(rtm_data)
        
        # Write output
        print(f'Writing Nextcloud Tasks file to: {output_file}')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        
        # Print statistics
        tasks = rtm_data.get('tasks', [])
        incomplete_tasks = sum(1 for t in tasks if not t.get('date_completed'))
        completed_tasks = sum(1 for t in tasks if t.get('date_completed'))
        
        print()
        print('✓ Conversion complete!')
        print(f'  Total tasks: {len(tasks)}')
        print(f'  - Incomplete: {incomplete_tasks}')
        print(f'  - Completed: {completed_tasks}')
        print()
        print('Import this file into Nextcloud Tasks via:')
        print('  Calendar app → Settings & Import → Import Calendar')
        
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
