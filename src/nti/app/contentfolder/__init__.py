#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from zope import interface

from zope.container.contained import Contained

from zope.traversing.interfaces import IPathAdapter

#: Content folder internal object 
CF_IO = 'cf.io'

@interface.implementer(IPathAdapter)
class CFIOPathAdapter(Contained):

    __name__ = CF_IO

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context
