#!/usr/bin/env python
# -*- coding: utf-8 -*-
import calendar
import hashlib
import itertools
import re
import time


pattern = ' '.join((
    r'(?P<timestamp>[-\d]{10} [:\d]{8})',
    r'(?P<host>\w+)',
    r'(?P<db>\w+):',
    r'\[(?P<hash>\w+)\]',
    r'(?P<url>[^\s]+)  ',
    r'Exception from line (?P<line>\d+)',
    r'of (?P<file>[^:]+):',
    r'(?P<message>.*)'
))

COMMON_PATH = '/usr/local/apache/common-local/'
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'


def parse_timestamp(ts):
    """Convert a timestamp to int UTC seconds since epoch."""
    return calendar.timegm(time.strptime(ts, TIMESTAMP_FORMAT))


def canonical_path(file):
    """Strip common path components."""
    if file.startswith(COMMON_PATH):
        file = file[len(COMMON_PATH):]
    return file


def get_signature(exception):
    hash = hashlib.sha1('%(file)s:%(line)s' % exception)
    return hash.hexdigest()[:10]


def parse_frame(frame):
    """Parse a line representing a frame in the trace."""
    frame = frame[frame.find(' ') + 1:]
    location, call = frame.split(': ', 1)
    b = location.find('(')
    if b != -1:
        file = location[:b]
        line = int(location[b + 1:-1])
        return dict(file=canonical_path(file), line=line, call=call)
    return dict(file=None, line=None, call=call)


def parse_trace(trace):
    """Parse a stack trace into a key/value map."""
    try:
        match = re.match(pattern, trace.pop(0))
        exception = match.groupdict()
        exception['line'] = int(exception['line'])
        exception['file'] = canonical_path(exception['file'])
        exception['file'] = canonical_path(exception.pop('file'))
        exception['signature'] = get_signature(exception)
        exception['timestamp'] = parse_timestamp(exception['timestamp'])
        exception['frames'] = [parse_frame(frame) for frame in trace]
    except (AttributeError, ValueError):
        # The regexp fails on database errors, which we don't care about
        # anyway, since they get logged by the database too.
        return None
    else:
        return exception


fatal_pattern = (r'\[(?P<timestamp>[^\]]+)\] Fatal error: (?P<message>.*) at '
                 r'(?P<file>\/[\S]+) on line (?P<line>\d+)')

"""
e.g.:
for line in open('fatal.log'):
    if line.startswith('[') and not re.match(pattern, line):
        print line
"""


def iter_exceptions(buffer):
    """Iterate over a buffer containing raw exceptions and yields parsed
    exception maps."""
    exceptions = (parse_trace(trace) for trace in iter_traces(buffer))
    return itertools.ifilter(None, exceptions)
