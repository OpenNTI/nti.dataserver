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

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.interfaces import IExternalObjectDecorator

from .interfaces import ILogonPong

@component.adapter(ILogonPong)
@interface.implementer(IExternalObjectDecorator)
class _SiteNameAdder(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, context, mapping):
		site = getSite()
		mapping['Site'] = site.__name__ if site is not None else None
