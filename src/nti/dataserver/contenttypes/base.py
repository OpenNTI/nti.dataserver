#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base functionality.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections

from zope import interface

from zope.deprecation import deprecate

from nti.common.property import alias

from nti.dataserver.interfaces import IModeledContent
from nti.dataserver.interfaces import IWritableShared
from nti.dataserver.interfaces import IUsernameIterable
from nti.dataserver.interfaces import IObjectSharingModifiedEvent

from nti.dataserver.users import User
from nti.dataserver.users import Entity

from nti.dataserver.sharing import ShareableMixin

from nti.dataserver_core.mixins import ZContainedMixin

from nti.dublincore.datastructures import CreatedModDateTrackingObject

from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.mimetype import mimetype

from nti.ntiids import ntiids

from nti.zodb.persistentproperty import PersistentPropertyHolder

def _get_entity(username, dataserver=None):
	return Entity.get_entity(username, dataserver=dataserver,
							 _namespace=User._ds_namespace)

@interface.implementer(IModeledContent)
class UserContentRoot(ShareableMixin,
					  ZContainedMixin,
					  CreatedModDateTrackingObject,
					  PersistentPropertyHolder):
	"""
	Base implementation of behaviours expected for contenttypes. Should be the primary
	superclass for subclasses.

	Subclasses must arrange for there to be an implementation of ``toExternalDictionary``.

	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	#: It is allowed to create instances of these classes from
	#: external data.
	__external_can_create__ = True

	__name__ = alias('id')  # this was previously at SelectedRange, but everything extends SelectedRange

	# TODO: Define containerId as an alias for __parent__.__name__ ? Right now they are completely separate,
	# and the __parent__ relationship is in fact initially established by the setting of containerId
	# in incoming data

	def __init__(self):
		super(UserContentRoot, self).__init__()

	__ext_ignore_toExternalObject__ = True
	@deprecate("Prefer to use nti.externalization directly.")
	def toExternalObject(self):
		return to_external_object(self)

	__ext_ignore_updateFromExternalObject__ = True
	@deprecate("Prefer to use nti.externalization directly.")
	def updateFromExternalObject(self, ext_object, context=None):
		return update_from_external_object(self, ext_object, context=context)

def _make_getitem(attr_name):
	def __getitem__(self, i):
		attr = getattr(self, attr_name)
		try:
			return attr[i]
		except TypeError:
			# For traversability purposes, we also accept
			# our string names as assigned in append
			# This could also be done with an adapter
			try:
				return attr[int(i)]
			except ValueError:  # can't convert to int
				raise KeyError(i)

	return __getitem__

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectIO

from nti.externalization.proxy import removeAllProxies

class UserContentRootInternalObjectIOMixin(object):

	validate_after_update = True

	# NOTE: inReplyTo and 'references' do not really belong here
	_excluded_out_ivars_ = { 'flattenedSharingTargetNames', 'flattenedSharingTargets',
							 'sharingTargets', 'inReplyTo', 'references' } | InterfaceObjectIO._excluded_out_ivars_

	context = alias('_ext_self')
	_orig_sharingTargets = None  # a cache for holding the targets before we update them

	def _ext_replacement(self):
		# TODO: The intid utility doesn't find objects if they are proxied. It unwraps
		# the security proxy, but we (the appserver) may be putting an Uncached proxy around them.
		# So we are unwrapping that here. Who should really be doing that?
		# TODO: This could break externalization triggered off interfaces added with a proxy
		# See also chatserver.messageinfo.
		return removeAllProxies(self.context)

	def toExternalObject(self, mergeFrom=None, **kwargs):
		extDict = super(UserContentRootInternalObjectIOMixin, self).toExternalObject(mergeFrom=mergeFrom, **kwargs)
		extDict['sharedWith'] = getattr(self.context, 'sharedWith', ())  # optional
		return extDict

	def _update_sharing_targets(self, sharedWith):
		# Replace sharing with the incoming data.

		targets = set()
		for s in sharedWith or ():
			target = s
			if _get_entity(s):
				target = _get_entity(s)
			elif hasattr(self.context.creator, 'getFriendsList'):
				# This branch is semi-deprecated. They should send in
				# the NTIID of the list...once we apply security here
				target = self.context.creator.getFriendsList(s)

			if (target is s or target is None) and ntiids.is_valid_ntiid_string(s):
				# Any thing else that is a username iterable,
				# in which we are contained (e.g., a class section we are enrolled in)
				# This last clause is our nod to security; need to be firmer

				obj = ntiids.find_object_with_ntiid(s)
				iterable = IUsernameIterable(obj, None)
				if iterable is not None:
					ents = set()
					for uname in iterable:
						ent = _get_entity(uname)
						if ent:
							ents.add(ent)
					if self.context.creator in ents:
						ents.discard(self.context.creator)  # don't let the creator slip in there
						target = tuple(ents)

			# We only add target, and only if it is non-none and
			# resolver. Otherwise we are falsely implying sharing
			# happened when it really didn't
			if target is not s and target is not None:
				targets.add(target or s)
		self.context.updateSharingTargets(targets)

	def updateFromExternalObject(self, ext_parsed, *args, **kwargs):
		assert isinstance(ext_parsed, collections.Mapping)
		parsed = ext_parsed
		# The pattern for subclasses is to pop the things that need special, non-dict handling,
		# and then to call super. When super returns, handle the special case
		sharedWith = parsed.pop('sharedWith', self)
		try:
			self.context.updateLastMod()
		except AttributeError:
			pass
		super(UserContentRootInternalObjectIOMixin, self).updateFromExternalObject(parsed, *args, **kwargs)

		if IWritableShared.providedBy(self.context) and sharedWith is not self:
			self._orig_sharingTargets = set(self.context.sharingTargets)
			self._update_sharing_targets(sharedWith)

	def _ext_adjust_modified_event(self, event):
		if self._orig_sharingTargets is not None:
			# Yes, we attempted to change the sharing settings.
			interface.alsoProvides(event, IObjectSharingModifiedEvent)
			event.oldSharingTargets = self._orig_sharingTargets
		return event

@interface.implementer(IInternalObjectIO)
class UserContentRootInternalObjectIO(UserContentRootInternalObjectIOMixin, InterfaceObjectIO):

	_ext_iface_upper_bound = IModeledContent

	# _excluded_out_ivars_ = { 'flattenedSharingTargetNames', 'flattenedSharingTargets',
	# 						   'sharingTargets', 'inReplyTo', 'references' } | InterfaceObjectIO._excluded_out_ivars_

	def __init__(self, context):
		super(UserContentRootInternalObjectIO, self).__init__(context)
