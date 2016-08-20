#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import Mapping

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from nti.externalization.interfaces import LocatedExternalDict

from nti.dataserver.interfaces import IStreamChangeEvent
from nti.dataserver.interfaces import IDynamicSharingTarget

from nti.dataserver.users.index import IX_EMAIL
from nti.dataserver.users.index import IX_TOPICS
from nti.dataserver.users.index import CATALOG_NAME
from nti.dataserver.users.index import IX_EMAIL_VERIFIED

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IAvatarURLProvider
from nti.dataserver.users.interfaces import IBackgroundURLProvider

from nti.property.urlproperty import UrlProperty

from nti.zodb import isBroken
from nti.zodb import readCurrent

# email

def get_catalog():
	return component.getUtility(ICatalog, name=CATALOG_NAME)

def verified_email_ids(email):
	email = email.lower()  # normalize
	catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

	# all ids w/ this email
	email_idx = catalog[IX_EMAIL]
	intids_emails = catalog.family.IF.Set(email_idx._fwd_index.get(email) or ())
	if not intids_emails:
		return catalog.family.IF.Set()

	# all verified emails
	verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
	intids_verified = catalog.family.IF.Set(verified_idx.getIds())

	# intersect
	result = catalog.family.IF.intersection(intids_emails, intids_verified)
	return result

def reindex_email_verification(user, catalog=None, intids=None):
	catalog = catalog if catalog is not None else get_catalog()
	intids = component.getUtility(IIntIds) if intids is None else intids
	uid = intids.queryId(user)
	if uid is not None:
		catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
		verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
		verified_idx.index_doc(uid, user)
		return True
	return False

def unindex_email_verification(user, catalog=None, intids=None):
	catalog = catalog if catalog is not None else get_catalog()
	intids = component.getUtility(IIntIds) if intids is None else intids
	uid = intids.queryId(user)
	if uid is not None:
		catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
		verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
		verified_idx.unindex_doc(uid)
		return True
	return False

def force_email_verification(user, profile=IUserProfile, catalog=None, intids=None):
	profile = profile(user, None)
	if profile is not None:
		profile.email_verified = True
		return reindex_email_verification(user, catalog=catalog, intids=intids)
	return False

def is_email_verified(email):
	result = verified_email_ids(email)
	return bool(result)

# broken objects

def _getId(obj, attribute='_ds_intid'):
	try:
		getattr(obj, attribute, None)
	except Exception:
		return None

def remove_broken_objects(user, include_containers=True, include_stream=True,
						  include_shared=True, include_dynamic_friends=False,
						  only_ntiid_containers=True):
		"""
		Returns an iterable across the NTIIDs that are relevant to this user.
		"""

		intids = component.queryUtility(IIntIds)
		attribute = intids.attribute

		result = LocatedExternalDict()

		def _remove(key, obj, container=None):
			if container is not None:
				del container[key]
				result[key] = str(type(obj))  # record

			uid = key
			if not isinstance(uid, int):
				uid = _getId(obj, attribute)

			if uid is not None:
				intids.forceUnregister(uid, notify=True, removeAttribute=False)

		def _loop_and_remove(container, unwrap=True):
			if isinstance(container, Mapping):
				readCurrent(container, False)
				f_unwrap = getattr(container, '_v_unwrap', lambda x:x)
				for key in list(container.keys()):
					value = container[key]
					value = f_unwrap(value) if unwrap else value
					if isBroken(value):
						_remove(key, value, container)
					elif IStreamChangeEvent.providedBy(value) and isBroken(value.object):
						_remove(key, value, container)

		if include_containers:
			for name, container in user.containers.iteritems():
				if not only_ntiid_containers or user._is_container_ntiid(name):
					_loop_and_remove(container, True)

		if include_stream:
			for name, container in user.streamCache.iteritems():
				if not only_ntiid_containers or user._is_container_ntiid(name):
					_loop_and_remove(container, False)

		if include_shared:

			for name, container in user.containersOfShared.items():
				if not only_ntiid_containers or user._is_container_ntiid(name):
					_loop_and_remove(container, False)

			if include_dynamic_friends:

				dynamic_friends = {	x for x in user.friendsLists.values()
						  			if IDynamicSharingTarget.providedBy(x) }

				interesting_dynamic_things = set(user.dynamic_memberships) | dynamic_friends
				for dynamic in interesting_dynamic_things:
					if include_shared and hasattr(dynamic, 'containersOfShared'):
						for name, container in dynamic.containersOfShared.items():
							if not only_ntiid_containers or user._is_container_ntiid(name):
								_loop_and_remove(container, False)

					if include_stream and hasattr(dynamic, 'streamCache'):
						for name, container in dynamic.streamCache.iteritems():
							if not only_ntiid_containers or user._is_container_ntiid(name):
								_loop_and_remove(container, False)
		return result

# properties

class ImageUrlProperty(UrlProperty):
	"""
	Adds a default value if nothing is set for the instance.

	Requires either a data: url or a complete URL, not a host-relative URL;
	host-relative URLs are ignored (as an attempt to update-in-place the same
	externalized URL).
	"""

	max_file_size = None
	avatar_field_name = u''
	avatar_provider_interface = None
	ignore_url_with_missing_host = True

	# TODO: Should we be scaling this now?
	# TODO: Should we be enforcing constraints on this? Like max size,
	# ensuring it really is an image, etc? With arbitrary image uploading, we risk
	# being used as a dumping ground for illegal/copyright infringing material
	def __get__(self, instance, owner):
		result = super(ImageUrlProperty, self).__get__(instance, owner)
		if not result and self.avatar_provider_interface is not None:
			adapted = self.avatar_provider_interface(instance.context)
			result = getattr(adapted, self.avatar_field_name, None)
		return result

class AvatarUrlProperty(ImageUrlProperty):
	max_file_size = 204800  # 200 KB
	avatar_field_name = 'avatarURL'
	avatar_provider_interface = IAvatarURLProvider

class BackgroundUrlProperty(ImageUrlProperty):
	max_file_size = 204800  # 200 KB
	avatar_field_name = 'backgroundURL'
	avatar_provider_interface = IBackgroundURLProvider
