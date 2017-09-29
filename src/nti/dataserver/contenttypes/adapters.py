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

from zope.annotation.factory import factory as an_factory

from persistent import Persistent

from nti.dataserver.interfaces import IContainerContext
from nti.dataserver.interfaces import IContextAnnotatable

logger = __import__('logging').getLogger(__name__)


@component.adapter(IContextAnnotatable)
@interface.implementer(IContainerContext)
class _ContainerContextAnnotation(Persistent):

    def __init__(self):
        self.context_id = None

_ContainerContext = an_factory(_ContainerContextAnnotation,
                               u'container_context')
