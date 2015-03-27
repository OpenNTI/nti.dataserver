#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base functionality.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from persistent import Persistent

from zope import interface
from zope import component
from zope.annotation.factory import factory as an_factory

from nti.dataserver.interfaces import IContainerContext
from nti.dataserver.interfaces import IContextAnnotatable

@component.adapter(IContextAnnotatable)
@interface.implementer(IContainerContext)
class _ContainerContextAnnotation( Persistent ):

	def __init__(self):
		self.context_id = None

_ContainerContext = an_factory( _ContainerContextAnnotation,
							'container_context' )
