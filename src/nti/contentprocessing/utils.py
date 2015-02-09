#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.component.interfaces import ComponentLookupError

from pyramid.threadlocal import get_current_request

from .interfaces import IAlchemyAPIKey

def get_possible_site_names(request=None, include_default=True):
	request = request or get_current_request()
	if not request:
		return () if not include_default else ('',)
	__traceback_info__ = request

	site_names = getattr(request, 'possible_site_names', ())
	if include_default:
		site_names += ('',)
	return site_names

def getAlchemyAPIKey(name=None, request=None, error=True):
	if name is not None:
		names = (name,)
	else:
		names = (name,) # get_possible_site_names(request)
	for name in names:
		result = component.queryUtility(IAlchemyAPIKey, name=name)
		if result is not None:
			break
	if error and result is None:
		raise ComponentLookupError(IAlchemyAPIKey, name)
	return result
