#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines the base behaviours for things that are threadable.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds
from zope.intid.interfaces import IIntIdAddedEvent
from zope.intid.interfaces import IIntIdRemovedEvent

from persistent.list import PersistentList

from nti.common import sets

from nti.containers.containers import IntidResolvingIterable

from nti.dataserver.interfaces import IThreadable
from nti.dataserver.interfaces import IInspectableWeakThreadable

from nti.externalization.oids import to_external_ntiid_oid

from nti.wref.interfaces import IWeakRef
from nti.wref.interfaces import IWeakRefToMissing

@interface.implementer(IInspectableWeakThreadable)
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

	# Our direct replies. Unlike _references, which is only changed
	# directly when this object changes, this can be mutated by many other
	# things. Therefore, we must maintain it as an object with good conflict
	# resolution. We use intid TreeSets both for this and for _referents.
	# Note that we actively maintain these values as objects are created
	# and deleted, so we are not concerned about intid reuse. We also
	# assume (as is the default in the mixin) that inReplyTo can only be
	# set at initial creation time, so we only watch for creations/deletions,
	# not modifications.
	_replies = ()

	# Our direct or indirect replies
	_referents = ()

	def __init__(self):
		super(ThreadableMixin, self).__init__()

	def getInReplyTo(self, allow_cached=True):
		"""
		Exposed for those times when we need explicit control over caching (when possible)
		"""
		if self._inReplyTo is None:
			return None

		try:
			return self._inReplyTo(allow_cached=allow_cached)
		except TypeError:  # Not ICachingWeakRef
			return self._inReplyTo()

	def setInReplyTo(self, value):
		self._inReplyTo = IWeakRef(value) if value is not None else None

	inReplyTo = property(getInReplyTo, setInReplyTo)

	def isOrWasChildInThread(self):
		return self._inReplyTo is not None or self._references

	@property
	def references(self):
		if not self._references:
			return ()

		return list(self.getReferences())

	def getReferences(self, allow_cached=True):
		for ref in (self._references or ()):
			try:
				val = ref(allow_cached=allow_cached)
			except TypeError:  # Not ICachingWeakRef
				val = ref()

			if val is not None:
				yield val

	def addReference(self, value):
		if value is not None:
			if self._references is ThreadableMixin._references:
				self._references = PersistentList()
			self._references.append(IWeakRef(value))

	def clearReferences(self):
		try:
			del self._references[:]
		except TypeError:
			pass  # The class tuple

	@property
	def replies(self):
		if self._replies is not ThreadableMixin._replies:
			return IntidResolvingIterable(self._replies, 
										  allow_missing=True, 
										  parent=self, 
										  name='replies')
		return ()
				
	@property
	def most_recent_reply(self):
		direct_replies = sorted((reply for reply in self.replies),
								key=lambda x: getattr(x,'createdTime', 0), 
								reverse=True)
		return direct_replies[0] if direct_replies else None
	
	mostRecentReply = most_recent_reply

	@property
	def referents(self):
		if self._referents is not ThreadableMixin._referents:
			return IntidResolvingIterable(self._referents, 
										  allow_missing=True, 
										  parent=self, 
										  name='referents')
		return ()

@component.adapter(IThreadable, IIntIdAddedEvent)
def threadable_added(threadable, event):
	"""
	Update the replies and referents. NOTE: This assumes that IThreadable is actually
	a ThreadableMixin.
	"""
	# Note that we don't trust the 'references' value of the client.
	# we build the reference chain ourself based on inReplyTo.
	inReplyTo = threadable.inReplyTo
	if not IThreadable.providedBy(inReplyTo):  # None in the real world, test case stuff otherwise
		return  # nothing to do

	intids = component.getUtility(IIntIds)
	intid = intids.getId(threadable)
	_threadable_added(threadable, intids, intid)

def _threadable_added(threadable, intids, intid):
	# This function is for migration support
	inReplyTo = threadable.inReplyTo
	if not IThreadable.providedBy(inReplyTo):
		return  # nothing to do

	# Only the direct parent gets added as a reply
	if inReplyTo._replies is ThreadableMixin._replies:
		inReplyTo._replies = intids.family.II.TreeSet()
	inReplyTo._replies.add(intid)

	# Now walk up the tree and record the indirect reference (including in the direct
	# parent)
	while IThreadable.providedBy(inReplyTo):
		if inReplyTo._referents is ThreadableMixin._referents:
			inReplyTo._referents = intids.family.II.TreeSet()
		inReplyTo._referents.add(intid)
		inReplyTo = inReplyTo.inReplyTo

@component.adapter(IThreadable, IIntIdRemovedEvent)
def threadable_removed(threadable, event):
	"""
	Update the replies and referents. NOTE: This assumes that IThreadable is actually a
	ThreadableMixin.
	"""
	# Note that we don't trust the 'references' value of the client.
	# we build the reference chain ourself based on inReplyTo.
	inReplyTo = threadable.inReplyTo
	if not IThreadable.providedBy(inReplyTo):
		return  # nothing to do

	intids = component.getUtility(IIntIds)
	intid = intids.getId(threadable)

	# Only the direct parent gets added as a reply
	try:
		sets.discard(inReplyTo._replies, intid)
	except AttributeError:
		pass

	# Now walk up the tree and record the indirect reference (including in the direct
	# parent)
	while IThreadable.providedBy(inReplyTo):
		try:
			sets.discard(inReplyTo._referents, intid)
		except AttributeError:
			pass
		inReplyTo = inReplyTo.inReplyTo

class ThreadableExternalizableMixin(object):
	"""
	Works with :class:`ThreadableMixin` with support for externalizing to and from a dictionary.
	Note that subclasses must extend something that is itself externalizable, and use
	cooperative super-class to be able to put this in the right order.

	The subclass can customize the way that references are externalized with the value
	of the :attr:`_ext_write_missing_references` attribute, as well as the methods
	:meth:`_ext_ref` and :meth:`_ext_can_update_threads`.

	The subclass must define the `_ext_replacement` function as the object being externalized.
	"""

	__external_oids__ = ['inReplyTo', 'references']  # Cause these to be resolved automatically

	#: If True (the default) then when objects that we are replies to or that
	#: we reference are deleted, we will write out placeholder missing values
	#: for them. Otherwise, there will be a null value or gap. See :const:`nti.ntiids.ntiids.TYPE_MISSING`
	_ext_write_missing_references = True

	def toExternalObject(self, mergeFrom=None, **kwargs):
		extDict = super(ThreadableExternalizableMixin, self).toExternalObject(mergeFrom=mergeFrom, **kwargs)
		if self._ext_can_write_threads():
			assert isinstance(extDict, collections.Mapping)
			context = self._ext_replacement()
			extDict['inReplyTo'] = self._ext_ref(context.inReplyTo, context._inReplyTo)
			extDict['references'] = [ self._ext_ref(ref(), ref) for ref in context._references ]
		return extDict

	def _ext_ref(self, obj, ref):
		"""
		Produce a string value for the object we reference (or are a reply to).
		By default, this will distinguish the three cases of never having been set,
		having been set and referring to an extant object, and having been set and
		now referring to an object that is deleted.
		"""
		if obj is not None:
			result = to_external_ntiid_oid(obj)
			if not result:
				__traceback_info__ = self, obj, ref
				raise ValueError("Unable to create external reference", obj)
			return result

		# No object. Did we have a reference at one time?
		if ref is not None and self._ext_write_missing_references:
			# Yes. Can we write something out?
			missing_ref = IWeakRefToMissing(ref, None)
			return missing_ref.make_missing_ntiid() if missing_ref is not None else None

	def updateFromExternalObject(self, parsed, **kwargs):
		assert isinstance(parsed, collections.Mapping)
		inReplyTo = parsed.pop('inReplyTo', None)
		references = parsed.pop('references', ())
		super(ThreadableExternalizableMixin, self).updateFromExternalObject(parsed, **kwargs)

		if self._ext_can_update_threads():
			context = self._ext_replacement()
			context.inReplyTo = inReplyTo
			context.clearReferences()
			for ref in references:
				context.addReference(ref)

	def _ext_can_update_threads(self):
		"""
		By default, once this object has been created and the thread-related values
		have been set, they cannot be changed by sending external data.

		(This depends on the context object being
		:class:`persistent.Persistent`, or otherwise defining the
		``_p_mtime`` property.)
		"""
		mod_time = getattr(self._ext_replacement(), '_p_mtime', None)
		return not mod_time

	def _ext_can_write_threads(self):
		"""
		Called to determine if we should even write the threadable
		properties to the dictionary. Sometimes subclasses may not want to.
		"""
		return True
