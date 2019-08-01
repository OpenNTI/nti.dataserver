#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides a tween that stores greenlet stats as it is switched into.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from gevent import getcurrent

from paste.deploy.converters import asbool

from zope import component

from nti.appserver.interfaces import IApplicationSettings

logger = __import__('logging').getLogger(__name__)


class _greenlet_request_tween(object):

    __slots__ = ('handler', 'enable_tween', 'switch_logging')

    def __init__(self, handler):
        settings = component.getUtility(IApplicationSettings)
        self.enable_tween = asbool(settings.get('greenlet_tween', True))
        self.switch_logging = asbool(settings.get('greenlet_tween_switch_logging', False))
        logger.info("Greenlet request tween (enabled=%s) (logging=%s)",
                    self.enable_tween, self.switch_logging)
        self.handler = handler

    def __call__(self, request):
        current = getcurrent()
        path = request.path
        enable_tween = self.enable_tween
        switch_logging = self.switch_logging

        current._nt_switch_into_count = 0
        original_switch = current.switch
        def _nt_switch(*args, **kwargs):
            if switch_logging:
                logger.info("Switching into greenlet (%s)", path)
            current._nt_switch_into_count += 1
            original_switch(*args, **kwargs)

        if enable_tween:
            current.switch = _nt_switch
        try:
            return self.handler(request)
        finally:
            request.environ['nti_greenlet_switch_into_count'] = current._nt_switch_into_count


def greenlet_request_tween_factory(handler, registry):
    return _greenlet_request_tween(handler)
