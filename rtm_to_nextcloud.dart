import 'dart:convert';
import 'dart:io';

void main(List<String> arguments) async {
  if (arguments.isEmpty) {
    print('Usage: dart rtm_to_nextcloud.dart <rtm_export.json> [output_file.ics]');
    print('');
    print('Converts Remember The Milk export to Nextcloud Tasks format (VCALENDAR/VTODO)');
    exit(1);
  }

  final inputFile = arguments[0];
  final outputFile = arguments.length > 1 
      ? arguments[1] 
      : inputFile.replaceAll('.json', '.ics');

  try {
    // Read and parse RTM export
    print('Reading RTM export from: $inputFile');
    final jsonContent = await File(inputFile).readAsString();
    final rtmData = jsonDecode(jsonContent) as Map<String, dynamic>;

    // Convert to VCALENDAR format
    print('Converting tasks to VCALENDAR/VTODO format...');
    final icsContent = convertRtmToIcs(rtmData);

    // Write output
    print('Writing Nextcloud Tasks file to: $outputFile');
    await File(outputFile).writeAsString(icsContent);

    // Print statistics
    final tasks = rtmData['tasks'] as List<dynamic>? ?? [];
    final incompleteTasks = tasks.where((t) => t['date_completed'] == null).length;
    final completedTasks = tasks.where((t) => t['date_completed'] != null).length;
    
    print('');
    print('✓ Conversion complete!');
    print('  Total tasks: ${tasks.length}');
    print('  - Incomplete: $incompleteTasks');
    print('  - Completed: $completedTasks');
    print('');
    print('Import this file into Nextcloud Tasks via:');
    print('  Calendar app → Settings & Import → Import Calendar');
    
  } catch (e) {
    print('Error: $e');
    exit(1);
  }
}

String convertRtmToIcs(Map<String, dynamic> rtmData) {
  final buffer = StringBuffer();
  
  // VCALENDAR header
  buffer.writeln('BEGIN:VCALENDAR');
  buffer.writeln('VERSION:2.0');
  buffer.writeln('PRODID:-//RTM to Nextcloud Converter//EN');
  buffer.writeln('CALSCALE:GREGORIAN');
  buffer.writeln('X-WR-CALNAME:RTM Tasks');
  
  // Get tasks
  final tasks = rtmData['tasks'] as List<dynamic>? ?? [];
  
  // Build list ID to name mapping
  final lists = <String, String>{};
  if (rtmData.containsKey('lists')) {
    for (final list in rtmData['lists'] as List<dynamic>) {
      lists[list['id'].toString()] = list['name'] as String;
    }
  }
  
  // Build notes mapping by series_id
  final notesBySeries = <String, List<Map<String, dynamic>>>{};
  if (rtmData.containsKey('notes')) {
    for (final note in rtmData['notes'] as List<dynamic>) {
      final noteMap = note as Map<String, dynamic>;
      final seriesId = noteMap['series_id']?.toString() ?? '';
      if (seriesId.isNotEmpty) {
        notesBySeries.putIfAbsent(seriesId, () => []);
        notesBySeries[seriesId]!.add(noteMap);
      }
    }
  }
  
  // Convert each task
  for (final task in tasks) {
    buffer.write(convertTaskToVtodo(task as Map<String, dynamic>, lists, notesBySeries));
  }
  
  // VCALENDAR footer
  buffer.writeln('END:VCALENDAR');
  
  return buffer.toString().replaceAll('\n', '\r\n');
}

String convertTaskToVtodo(Map<String, dynamic> task, Map<String, String> lists, Map<String, List<Map<String, dynamic>>> notesBySeries) {
  final buffer = StringBuffer();
  buffer.writeln('BEGIN:VTODO');
  
  // UID - unique identifier
  final uid = 'rtm-${task['id']}';
  buffer.writeln('UID:$uid');
  
  // RELATED-TO - for subtasks (parent-child relationship)
  // RTM uses parent_id to indicate a task is a subtask
  if (task.containsKey('parent_id') && task['parent_id'] != null) {
    final parentUid = 'rtm-${task['parent_id']}';
    buffer.writeln('RELATED-TO:$parentUid');
  }
  
  // SUMMARY - task name
  final summary = escapeIcalText(task['name'] ?? 'Untitled Task');
  buffer.writeln('SUMMARY:$summary');
  
  // PRIORITY
  if (task.containsKey('priority') && task['priority'] != null) {
    final priority = convertPriority(task['priority'] as String);
    if (priority > 0) {
      buffer.writeln('PRIORITY:$priority');
    }
  }
  
  // DUE - due date
  if (task.containsKey('date_due') && task['date_due'] != null) {
    final hasDueTime = task['has_due_time'] as bool? ?? false;
    final dueDate = formatDateTime(task['date_due'] as int, hasDueTime);
    if (dueDate != null) {
      if (hasDueTime) {
        buffer.writeln('DUE:$dueDate');
      } else {
        buffer.writeln('DUE;VALUE=DATE:$dueDate');
      }
    }
  }
  
  // DTSTART - start date
  if (task.containsKey('date_start') && task['date_start'] != null) {
    final hasStartTime = task['has_start_time'] as bool? ?? false;
    final startDate = formatDateTime(task['date_start'] as int, hasStartTime);
    if (startDate != null) {
      if (hasStartTime) {
        buffer.writeln('DTSTART:$startDate');
      } else {
        buffer.writeln('DTSTART;VALUE=DATE:$startDate');
      }
    }
  }
  
  // STATUS and COMPLETED
  if (task.containsKey('date_completed') && task['date_completed'] != null) {
    buffer.writeln('STATUS:COMPLETED');
    final completedDate = formatDateTime(task['date_completed'] as int, true);
    if (completedDate != null) {
      buffer.writeln('COMPLETED:$completedDate');
    }
  } else {
    buffer.writeln('STATUS:NEEDS-ACTION');
  }
  
  // CREATED - creation date
  if (task.containsKey('date_created') && task['date_created'] != null) {
    final createdDate = formatDateTime(task['date_created'] as int, true);
    if (createdDate != null) {
      buffer.writeln('CREATED:$createdDate');
    }
  }
  
  // LAST-MODIFIED - modification date
  if (task.containsKey('date_modified') && task['date_modified'] != null) {
    final modifiedDate = formatDateTime(task['date_modified'] as int, true);
    if (modifiedDate != null) {
      buffer.writeln('LAST-MODIFIED:$modifiedDate');
    }
  }
  
  // RRULE - recurrence rule
  if (task.containsKey('repeat') && task['repeat'] != null) {
    final rrule = task['repeat'] as String;
    if (rrule.isNotEmpty) {
      buffer.writeln('RRULE:$rrule');
    }
  }
  
  // URL - task URL
  if (task.containsKey('url') && task['url'] != null) {
    final url = escapeIcalText(task['url'] as String);
    buffer.writeln('URL:$url');
  }
  
  // CATEGORIES - tags and list name
  final categories = <String>[];
  
  if (task.containsKey('tags') && task['tags'] != null) {
    categories.addAll((task['tags'] as List<dynamic>).cast<String>());
  }
  
  // Add list name to categories
  final listId = task['list_id']?.toString() ?? '';
  if (listId.isNotEmpty && lists.containsKey(listId)) {
    categories.add(lists[listId]!);
  }
  
  if (categories.isNotEmpty) {
    final cats = categories.map(escapeIcalText).join(',');
    buffer.writeln('CATEGORIES:$cats');
  }
  
  // DESCRIPTION - combine all notes for this task's series_id
  final descriptionParts = <String>[];
  
  final seriesId = task['series_id']?.toString() ?? '';
  if (seriesId.isNotEmpty && notesBySeries.containsKey(seriesId)) {
    for (final note in notesBySeries[seriesId]!) {
      final noteText = note['text'] as String? ?? '';
      if (noteText.isNotEmpty) {
        descriptionParts.add(noteText);
      }
    }
  }
  
  if (descriptionParts.isNotEmpty) {
    final description = escapeIcalText(descriptionParts.join('\n\n'));
    buffer.writeln('DESCRIPTION:$description');
  }
  
  // Custom properties for RTM-specific data
  if (task.containsKey('postpone_count') && task['postpone_count'] != null) {
    buffer.writeln('X-RTM-POSTPONE-COUNT:${task['postpone_count']}');
  }
  
  if (task.containsKey('source') && task['source'] != null) {
    final source = escapeIcalText(task['source'] as String);
    buffer.writeln('X-RTM-SOURCE:$source');
  }
  
  buffer.writeln('END:VTODO');
  return buffer.toString();
}

String escapeIcalText(String text) {
  if (text.isEmpty) return '';
  
  return text
      .replaceAll('\\', '\\\\')
      .replaceAll(',', '\\,')
      .replaceAll(';', '\\;')
      .replaceAll('\n', '\\n');
}

String? formatDateTime(int timestampMs, bool hasTime) {
  final dt = DateTime.fromMillisecondsSinceEpoch(timestampMs);
  
  if (hasTime) {
    // Format: YYYYMMDDTHHMMSS
    return '${dt.year.toString().padLeft(4, '0')}'
           '${dt.month.toString().padLeft(2, '0')}'
           '${dt.day.toString().padLeft(2, '0')}'
           'T'
           '${dt.hour.toString().padLeft(2, '0')}'
           '${dt.minute.toString().padLeft(2, '0')}'
           '${dt.second.toString().padLeft(2, '0')}';
  } else {
    // Format: YYYYMMDD (date only)
    return '${dt.year.toString().padLeft(4, '0')}'
           '${dt.month.toString().padLeft(2, '0')}'
           '${dt.day.toString().padLeft(2, '0')}';
  }
}

int convertPriority(String rtmPriority) {
  // RTM: P1 (highest), P2, P3 (lowest), or None
  // iCalendar: 1 (highest) to 9 (lowest), 0 = undefined
  const priorityMap = {
    'P1': 1,
    'P2': 5,
    'P3': 9,
  };
  return priorityMap[rtmPriority] ?? 0;
}
