#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from paste.deploy.converters import asint

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.appserver.interfaces import IApplicationSettings

from nti.socketio.interfaces import ISocketSessionSettings

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ISocketSessionSettings)
class SocketSessionSettings(object):

    @Lazy
    def _settings(self):
        return component.getUtility(IApplicationSettings)

    @Lazy
    def SessionCleanupAge(self):
        result = self._settings.get('session_cleanup_age')
        return asint(result) if result is not None else result

    @Lazy
    def SessionPingFrequency(self):
        result = self._settings.get('session_ping_frequency')
        return asint(result) if result is not None else result

    @Lazy
    def SessionServerHeartbeatUpdateFrequency(self):
        result = self._settings.get('session_reader_heartbeat_update_frequency')
        return asint(result) if result is not None else result

    @Lazy
    def SessionServerHeartbeatTimeout(self):
        result = self._settings.get('session_server_heartbeat_timeout')
        return asint(result) if result is not None else result
