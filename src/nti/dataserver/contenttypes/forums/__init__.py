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
from nti.utils.property import alias as _alias

class _CreatedNamedNTIIDMixin(object):
	"""
	Mix this in to get NTIIDs based on the creator and name.
	You must define the ``ntiid_type``.

	.. py:attribute:: _ntiid_type
		The string constant for the type of the NTIID.

	.. py:attribute:: _ntiid_include_parent_name
		If True (not the default) the ``__name__`` of our ``__parent__``
		object is included in the specific part, preceding our name
		and separated by a dot. Use this if our name is only unique within
		our parent. (We choose a dot because it is not used by :func:`.make_specific_safe`.)

	"""

	creator = None
	__name__ = None

	_ntiid_include_parent_name = False
	_ntiid_type = None

	@property
	def _ntiid_creator_username(self):
		return self.creator.username if self.creator else None

	@property
	def _ntiid_specific_part(self):
		if not self._ntiid_include_parent_name:
			return self.__name__
		try:
			return self.__parent__.__name__ + '.' + self.__name__
		except AttributeError: # Not ready yet
			return None

	@_CachedProperty('_ntiid_creator_username','_ntiid_specific_part')
	def NTIID(self):
		"""
		NTIID is defined only after the _ntiid_creator_username is
		set; until then it is none. We cache based on this value and
		our specific part (which includes our __name__)
		"""
		creator_name = self._ntiid_creator_username
		if creator_name:
			return _make_ntiid( date=_NTIID_DATE,
								provider=creator_name,
								nttype=self._ntiid_type,
								specific=self._ntiid_specific_part )


def _containerIds_from_parent():
	"Returns a tuple of properties to assign to id and containerId"

	# BWC: Some few objects will have this is their __dict__, but that's OK, it should
	# match what we get anyway (and if it doesn't, its wrong)

	# TODO: Cache this?
	def _get_containerId(self):
		if self.__parent__ is not None:
			try:
				return self.__parent__.NTIID
			except AttributeError:
				# Legacy support: the parent is somehow dorked up. If we have one in
				# our __dict__ still, use it. Otherwise, let the error
				# propagate.
				if 'containerId' in self.__dict__:
					return self.__dict__['containerId']
				raise

	def _set_containerId(self, cid ):
		pass # ignored

	# Unlike the superclass, we define the nti_interfaces.IContained properties
	# as aliases for the zope.container.IContained values

	return _alias('__name__'),  property(_get_containerId, _set_containerId)
