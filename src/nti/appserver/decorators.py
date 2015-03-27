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
from zope.component.hooks import getSite

from nti.dataserver.interfaces import IContainerContext
from nti.dataserver.interfaces import IContextAnnotatable

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from .interfaces import ILogonPong

@component.adapter(ILogonPong)
@interface.implementer(IExternalObjectDecorator)
class _SiteNameAdder(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, context, mapping):
		site = getSite()
		mapping['Site'] = site.__name__ if site is not None else None

@interface.implementer(IExternalMappingDecorator)
@component.adapter(IContextAnnotatable)
class _ContainerContextDecorator(object):
	"""
	For :class:`~.IContextAnnotatable` objects, decorate the
	result with the context_id.
	"""
	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		container_context = IContainerContext( context, None )
		if container_context:
			mapping['ContainerContext'] = container_context.context_id
