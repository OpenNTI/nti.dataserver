#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content-unit prefernce decorators.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface
from zope import component

from nti.appserver.interfaces import IContentUnitInfo
from nti.externalization.interfaces import IExternalMappingDecorator
from pyramid.interfaces import IRequest

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from .prefs import find_prefs_for_content_and_user
from .prefs import prefs_present

@interface.implementer(IExternalMappingDecorator)
@component.adapter(IContentUnitInfo, IRequest)
class _ContentUnitPreferencesDecorator(AbstractAuthenticatedRequestAwareDecorator):
	"Decorates the mapping with the sharing preferences"""

	def _predicate(self, context, result):
		return self._is_authenticated and context.contentUnit is not None

	def _do_decorate_external(self, context, result):
		prefs, provenance, contentUnit = find_prefs_for_content_and_user(context.contentUnit, self.remoteUser)

		if prefs_present( prefs ):
			ext_obj = {}
			ext_obj['State'] = 'set' if contentUnit is context.contentUnit else 'inherited'
			ext_obj['Provenance'] = provenance
			ext_obj['sharedWith'] = prefs.sharedWith
			ext_obj['Class'] = 'SharingPagePreference'

			result['sharingPreference'] = ext_obj

		if prefs:
			# We found one, but it specified no sharing settings.
			# we still want to copy its last modified
			if prefs.lastModified > context.lastModified:
				result['Last Modified'] = prefs.lastModified
				context.lastModified = prefs.lastModified
