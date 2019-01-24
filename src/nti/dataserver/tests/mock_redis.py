#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Import this module to access a mock redis implementation named `InMemoryMockRedis`.
Prefer importing this module over directly importing :mod:`fakeredis`
so that the proper cleanups are established.

$Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import is_
from hamcrest import any_of
from hamcrest import assert_that
from hamcrest import instance_of
from hamcrest import greater_than_or_equal_to

import numbers
import datetime
import threading

import fakeredis

from zope import interface

from nti.dataserver.interfaces import IRedisClient
interface.classImplements(fakeredis.FakeStrictRedis,
                          IRedisClient)

InMemoryMockRedis = fakeredis.FakeStrictRedis  # BWC alias

# Test for pubsub support and hack in some basics if needed
if not hasattr(InMemoryMockRedis, 'pubsub'):

    class PubSub(object):

        def __init__(self, redis):
            self._redis = redis
            self._subscribed = []

        def subscribe(self, channel):
            self._subscribed.append(channel)
            # Which also fires an event into the channel
            self._redis._get_channel(channel).append({'type': 'subscibed'})

        def listen(self):
            for channel in self._subscribed:
                channel = self._redis._get_channel(channel)
                for msg in channel:
                    yield msg
                del channel[:]

        def unsubscribe(self, channel):
            self._subscribed.remove(channel)

    InMemoryMockRedis.pubsub = lambda self: PubSub(self)

    def publish(self, channel, message):
        self._get_channel(channel).append(message)

    def _get_channel(self, channel):
        channels = getattr(self, '_channels', None)
        if channels is None:
            channels = {}
            self._channels = channels

        return channels.setdefault(channel, [])

    InMemoryMockRedis.publish = publish
    InMemoryMockRedis._get_channel = _get_channel

# XXX: Dont' think we need this anymore, causes an AttributeError with redis3.0
# # Pretend to have a closeable connection pool
# if not hasattr(InMemoryMockRedis, 'connection_pool'):
#
#     class Pool(object):
#
#         def disconnect(self):
#             pass
#
#     InMemoryMockRedis.connection_pool = property(lambda unused_s: Pool())

# Pretend to have a lock
if not hasattr(InMemoryMockRedis, 'lock'):
    class _Lock(object):
        def __init__(self):
            self._lock = threading.Lock()

        def acquire(self, **unused_kwargs):
            return self._lock.acquire()

        def release(self):
            self._lock.release()

        def __enter__(self):
            self._lock.acquire()

        def __exit__(self, *unused_args, **unused_kwargs):
            self._lock.release()

    def _get_lock(self, *unused_args, **unused_kwargs):
        return _Lock()
    InMemoryMockRedis.lock = _get_lock

# Enforce the type of time arguments for some methods
# that are commonly mixed up (these arguments are
# ignored my fakeredis)


def _check_time(time):
    assert_that(time, any_of(instance_of(numbers.Rational),
                             instance_of(datetime.timedelta)))
    if isinstance(time, numbers.Rational):
        assert_that(time, is_(greater_than_or_equal_to(0)))

_orig_setex = InMemoryMockRedis.setex


def _setex(self, name, time, value):
    _check_time(time)
    if isinstance(time, datetime.timedelta):
        time = int(time.total_seconds())
    _orig_setex(self, name, time, value)

InMemoryMockRedis.setex = _setex
