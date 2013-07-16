#!/usr/bin/env python
# -*- coding: utf-8 -*-
import zmq

ctx = zmq.Context.instance()
sock = ctx.socket(zmq.SUB)
sock.connect(b'tcp://localhost:8423')
sock.setsockopt(zmq.SUBSCRIBE, b'')


def iter_errors(callback):
    """Coroutine. Assembles complete traces and passes them to `callback`."""
    line = ''
    # The first trace is likely incomplete, so discard it.
    while not line.endswith('{main}'):
        line = (yield)

    buffer = []
    while 1:
        line = (yield)
        buffer.append(line)
        if line.endswith('{main}'):
            callback(buffer)
            buffer = []


def handle_exception(buf):
    print 'Exception: ', buf


def handle_fatal(buf):
    print 'Fatal: ', buf


# Map error types to coroutines.
processors = {
    'fatal': iter_errors(handle_fatal),
    'exception': iter_errors(handle_exception),
}


# Initialize coroutines.
for processor in processors.values():
    processor.send(None)


# Iterate stream and send lines to the right coroutine.
while 1:
    line = sock.recv_unicode()
    seq_id, type, line = line.split(' ', 2)
    processors[type].send(line.strip())
