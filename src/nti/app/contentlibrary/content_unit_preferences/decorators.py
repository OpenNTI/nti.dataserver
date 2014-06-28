#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for exposing the content library to clients.

In addition to providing access to the content, this

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


import time
import itertools
import persistent


from zope import interface
from zope import component


from zope.annotation.factory import factory as an_factory

from pyramid.threadlocal import get_current_request

from nti.appserver import interfaces as app_interfaces
from .interfaces import IContentUnitPreferences


from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import users

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IDynamicSharingTarget
from nti.dataserver.interfaces import ICommunity

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

from nti.ntiids import ntiids

def _prefs_present( prefs ):
	"""
	Does `prefs` represent a valid preference stored by the user?
	Note that even a blank, empty set of targets is a valid preference;
	a None value removes the preference.
	"""
	return prefs and prefs.sharedWith is not None

class _FallbackPrefs(object):
	__slots__ = (b'sharedWith',)

	def __init__(self, sharedWith=()):
		self.sharedWith = sharedWith

	@property
	def lastModified(self):
		return 0

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(app_interfaces.IContentUnitInfo)
class _ContentUnitPreferencesDecorator(object):
	"Decorates the mapping with the sharing preferences. Contains the algorithm to resolve them."

	__metaclass__ = SingletonDecorator

	def _find_prefs(self, context, remote_user):
		# Walk up the parent tree of content units (not including the mythical root)
		# until we run out, or find preferences
		def units( ):
			contentUnit = context.contentUnit
			while lib_interfaces.IContentUnit.providedBy( contentUnit ):
				yield contentUnit, contentUnit.ntiid, contentUnit.ntiid
				contentUnit = contentUnit.__parent__
		# Also include the root
		root = ((None, '', ntiids.ROOT),)
		# We will go at least once through this loop
		contentUnit = provenance = prefs = None
		for contentUnit, containerId, provenance in itertools.chain( units(), iter(root) ):
			container = remote_user.getContainer( containerId )
			prefs = IContentUnitPreferences( container, None )
			if _prefs_present( prefs ):
				break
			prefs = None

		if not _prefs_present( prefs ):
			# OK, nothing found by querying the user. What about looking at
			# the units themselves?
			for contentUnit, containerId, provenance in units():
				prefs = IContentUnitPreferences( contentUnit, None )
				if _prefs_present( prefs ):
					break
				prefs = None

		if not _prefs_present( prefs ):
			# Ok, nothing the user has set, and nothing found looking at the content
			# units themselves. Now we're into weird fallback territory. This is probably very shaky and
			# needing constant review, but it's a start.
			dfl_name = None
			for dynamic_member in remote_user.dynamic_memberships:
				# Can we find a DynamicFriendsList/DFL/Team that the user belongs too?
				# And just one? If so, then it's our default sharing target
				if IDynamicSharingTarget.providedBy( dynamic_member ) and not ICommunity.providedBy( dynamic_member ):
					# Found one...
					if dfl_name is None:
						# and so far just one
						dfl_name = dynamic_member.NTIID
					else:
						# damn, more than one.
						dfl_name = None
						break
			if dfl_name:
				# Yay, found one!
				prefs = _FallbackPrefs( sharedWith=(dfl_name,) )
				provenance = dfl_name

		return prefs, provenance, contentUnit

	def decorateExternalMapping( self, context, result_map ):
		if context.contentUnit is None:
			return

		request = get_current_request()
		if not request:
			return
		remote_user = users.User.get_user( request.authenticated_userid,
										   dataserver=component.getUtility(IDataserver) )
		if not remote_user:
			return

		prefs, provenance, contentUnit = self._find_prefs( context, remote_user )

		if _prefs_present( prefs ):
			ext_obj = {}
			ext_obj['State'] = 'set' if contentUnit is context.contentUnit else 'inherited'
			ext_obj['Provenance'] = provenance
			ext_obj['sharedWith'] = prefs.sharedWith
			ext_obj['Class'] = 'SharingPagePreference'

			result_map['sharingPreference'] = ext_obj

		if prefs:
			# We found one, but it specified no sharing settings.
			# we still want to copy its last modified
			if prefs.lastModified > context.lastModified:
				result_map['Last Modified'] = prefs.lastModified
				context.lastModified = prefs.lastModified
