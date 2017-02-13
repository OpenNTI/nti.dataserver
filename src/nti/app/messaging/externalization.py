#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.app.messaging.interfaces import IConversation

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectExternalizer


@component.adapter(IConversation)
@interface.implementer(IInternalObjectExternalizer)
class _ConversationExternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = IConversation

    _excluded_out_ivars_ = {'Participants'} | InterfaceObjectIO._excluded_out_ivars_

    def toExternalObject(self, **kwargs):
        context = self._ext_replacement()
        result = super(_ConversationExternalizer, self).toExternalObject(**kwargs)
        result['Participants'] = [p.id for p in context.Participants or ()]
        return result
