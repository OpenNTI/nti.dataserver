#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines the base behaviours for things that are threadable.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

import collections

from persistent.list import PersistentList

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization import integer_strings

from nti.ntiids import ntiids

from nti.dataserver import interfaces as nti_interfaces


class ThreadableMixin(object):
	"""
	Defines an object that is client-side threadable. These objects are
	`threaded like email`_. We assume a single parent and
	maintain a list of ancestors in order up to the root (or the last
	thing that was threadable). These references are weakly maintained
	(see :class:`.IWeakRef`) so when the objects go away the properties (eventually)
	clear as well.

	.. _threaded like email: http://www.jwz.org/doc/threading.html
	"""

	# Our one single parent
	_inReplyTo = None
	# Our chain of references back to the root
	_references = ()

	def __init__(self):
		super(ThreadableMixin,self).__init__()

	def getInReplyTo(self):
		return self._inReplyTo() if self._inReplyTo else None

	def setInReplyTo( self, value ):
		self._inReplyTo = nti_interfaces.IWeakRef( value ) if value is not None else None

	inReplyTo = property( getInReplyTo, setInReplyTo )

	@property
	def references(self):
		if not self._references:
			return ()

		return [x() for x in self._references if x() is not None]

	def addReference( self, value ):
		if value is not None:
			if self._references is ThreadableMixin._references:
				self._references = PersistentList()
			self._references.append( nti_interfaces.IWeakRef( value ) )

	def clearReferences( self ):
		try:
			del self._references[:]
		except TypeError:
			pass # The class tuple

class ThreadableExternalizableMixin(ThreadableMixin):
	"""
	Extends :class:`ThreadableMixin` with support for externalizing to and from a dictionary.
	Note that subclasses must extend something that is itself externalizable, and use
	cooperative super-class to be able to put this in the right order.

	The subclass can customize the way that references are externalized with the value
	of the :attr:`_ext_write_missing_references` attribute, as well as the methods
	:meth:`_ext_ref` and :meth:`_ext_can_update_threads`.
	"""

	__external_oids__ = ['inReplyTo', 'references'] # Cause these to be resolved automatically

	#: If True (the default) then when objects that we are replies to or that
	#: we reference are deleted, we will write out placeholder missing values
	#: for them. Otherwise, there will be a null value or gap. See :const:`nti.ntiids.ntiids.TYPE_MISSING`
	_ext_write_missing_references = True

	def toExternalObject(self):
		extDict = super(ThreadableExternalizableMixin,self).toExternalObject()
		assert isinstance( extDict, collections.Mapping )

		extDict['inReplyTo'] = self._ext_ref( self.inReplyTo, self._inReplyTo )
		extDict['references'] = [ self._ext_ref( ref(), ref ) for ref in self._references ]
		return extDict

	def _ext_ref( self, obj, ref ):
		"""
		Produce a string value for the object we reference (or are a reply to).
		By default, this will distinguish the three cases of never having been set,
		having been set and referring to an extant object, and having been set and
		now referring to an object that is deleted.
		"""
		if obj is not None:
			result = to_external_ntiid_oid( obj )
			if not result:
				raise ValueError( "Unable to create external reference", obj )
			return result

		# No object. Did we have a reference at one time?
		if ref is not None and self._ext_write_missing_references:
			# Yes. Can we write something out?
			missing_ref = nti_interfaces.IWeakRefToMissing( ref, None )
			return missing_ref.make_missing_ntiid() if missing_ref is not None else None

	def updateFromExternalObject( self, parsed, **kwargs ):
		assert isinstance( parsed, collections.Mapping )
		inReplyTo = parsed.pop( 'inReplyTo', None )
		references = parsed.pop( 'references', () )
		super(ThreadableExternalizableMixin, self).updateFromExternalObject( parsed, **kwargs )

		if self._ext_can_update_threads():
			self.inReplyTo = inReplyTo
			self.clearReferences()
			for ref in references:
				self.addReference( ref )

	def _ext_can_update_threads( self ):
		"""
		By default, once this object has been created and the thread-related values
		have been set, they can not be changed by sending external data.

		(This depends on subclasses being
		:class:`persistent.Persistent`, or otherwise defining the
		``_p_mtime`` property.)
		"""
		mod_time = getattr( self, '_p_mtime', None )
		return not mod_time
