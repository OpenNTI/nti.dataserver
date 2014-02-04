# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from . import interfaces as search_interfaces

@interface.implementer(search_interfaces.ISearchHitPredicate)
@component.adapter(search_interfaces.ISearchHit)
class _DefaultSearchHitPredicate(object):
	
	__slots__ = ()

	def __init__(self, hit):
		pass

	def allow(self, hit):
		return True

