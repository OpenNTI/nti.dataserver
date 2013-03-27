#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Package containing forum support.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')


try:
	from Acquisition import aq_parent

	class _AcquiredSharingTargetsProperty(object):

		def __get__( self, instance, klass ):
			if instance is None:
				return self
			# NOTE: This only works if __parent__ is already set. It fails
			# otherwise
			return getattr( aq_parent( instance ), 'sharingTargets', () )

		def __set__( self, instance, value ):
			return # Ignored
except ImportError:
	# Acquisition not available
	class _AcquiredSharingTargetsProperty(object):
		def __get__( self, instance, klass ):
			if instance is None:
				return self
			p = getattr( instance, '__parent__', None )
			while p is not None:
				targets = getattr( p, 'sharingTargets', None )
				if targets is not None:
					return targets
				p = getattr( instance, '__parent__', None )
			return ()
		def __set__( self, instance, value ):
			return

from nti.ntiids.ntiids import make_ntiid as _make_ntiid
from nti.ntiids.ntiids import DATE as _NTIID_DATE
from nti.utils.property import CachedProperty as _CachedProperty


class _CreatedNamedNTIIDMixin(object):
	"""
	Mix this in to get NTIIDs based on the creator and name.
	You must define the ``ntiid_type``.

	.. py:attribute:: ntiid_type
		The string constant for the type of the NTIID.

	.. py:attribute:: ntiid_include_parent_name
		If True (not the default) the ``__name__`` of our ``__parent__``
		object is included in the specific part, preceding our name
		and separated by a dot. Use this if our name is only unique within
		our parent. (We choose a dot because it is not used by :func:`.make_specific_safe`.)

	"""

	creator = None
	__name__ = None
	ntiid_type = None
	ntiid_include_parent_name = False

	@property
	def ntiid_creator_username(self):
		return self.creator.username

	@_CachedProperty('__name__') # But __parent__ and creator are not necessarily safe
	def NTIID(self):
		"NTIID is defined only after the creator is set"
		return _make_ntiid( date=_NTIID_DATE,
							provider=self.ntiid_creator_username,
							nttype=self.ntiid_type,
							specific=self.__name__ if not self.ntiid_include_parent_name else self.__parent__.__name__ + '.' + self.__name__)
