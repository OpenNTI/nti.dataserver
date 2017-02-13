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

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.messaging.interfaces import IMessage

from nti.threadable.externalization import ThreadableExternalizableMixin


class _AbstractUsersExternalizerMixin(object):

    _excluded_out_ivars_ = {'To', 'From'}

    def externalize_users(self, external, context):
        external['From'] = context.From.id
        external['To'] = [recipient.id for recipient in context.To]


@component.adapter(IMessage)
@interface.implementer(IInternalObjectExternalizer)
class _MessageExternalizer(_AbstractUsersExternalizerMixin,
                           ThreadableExternalizableMixin,
                           InterfaceObjectIO):

    _ext_iface_upper_bound = IMessage

    _excluded_out_ivars_ =  _AbstractUsersExternalizerMixin._excluded_out_ivars_ | \
                            InterfaceObjectIO._excluded_out_ivars_

    def _ext_can_write_threads(self):
        return False

    def toExternalObject(self, **kwargs):
        context = self._ext_replacement()
        result = super(_MessageExternalizer, self).toExternalObject(**kwargs)
        self.externalize_users(result, context)
        return result
