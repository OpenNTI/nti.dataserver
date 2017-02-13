#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component
from zope import interface

from zope.security.interfaces import IPrincipal

from nti.externalization.interfaces import IInternalObjectUpdater

from nti.externalization.datastructures import InterfaceObjectIO

from nti.messaging.interfaces import IPeerToPeerMessage

from nti.threadable.externalization import ThreadableExternalizableMixin


class MessageIOBase(ThreadableExternalizableMixin, InterfaceObjectIO):

    def _principal(self, obj):
        return IPrincipal(obj)

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        if 'From' in parsed:
            parsed['From'] = self._principal(parsed['From'])

        if 'To' in parsed:
            to = parsed['To']
            if isinstance(to, six.string_types):
                to = (to,)
            parsed['To'] = [self._principal(receipient) for receipient in to]

        result = super(MessageIOBase,
					   self).updateFromExternalObject(parsed, *args, **kwargs)
        return result


@component.adapter(IPeerToPeerMessage)
@interface.implementer(IInternalObjectUpdater)
class PeerToPeerHousingMessage(MessageIOBase):

    _ext_iface_upper_bound = IPeerToPeerMessage

    def _principal(self, obj):
        username = getattr(obj, 'username', obj)
        return IPrincipal(username)
