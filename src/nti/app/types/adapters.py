#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.appserver.interfaces import IEditLinkMaker

from nti.chatserver.interfaces import IMeeting

logger = __import__('logging').getLogger(__name__)


@component.adapter(IMeeting)
@interface.implementer(IEditLinkMaker)
class _MeetingEditLinkMaker(object):

    __slots__ = ()

    def __init__(self, *args, **kwargs):
        pass

    def make(self, *unused_args, **unused_kwargs):
        return None
