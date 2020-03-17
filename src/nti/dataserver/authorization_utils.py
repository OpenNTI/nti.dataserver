#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

__docformat__ = "restructuredtext en"

import contextlib

from zope.security import management

from zope.security.interfaces import IParticipation

from zope.security.management import endInteraction
from zope.security.management import newInteraction
from zope.security.management import queryInteraction

from nti.dataserver.interfaces import IPrincipal

logger = __import__('logging').getLogger(__name__)


@contextlib.contextmanager
def zope_interaction(username):
    interaction = queryInteraction()
    previous_interaction = getattr(management.thread_local, 'previous_interaction', None)
    endInteraction()
    participation = IParticipation(IPrincipal(username))
    newInteraction(participation)
    try:
        yield
    finally:
        if interaction is not None:
            management.thread_local.interaction = interaction
        elif hasattr(management.thread_local, 'interaction'):
            del management.thread_local.interaction
        if previous_interaction is not None:
            management.thread_local.previous_interaction = previous_interaction
        elif hasattr(management.thread_local, 'previous_interaction'):
            del management.thread_local.previous_interaction
