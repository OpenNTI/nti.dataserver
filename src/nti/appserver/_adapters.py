#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AppSever adapters.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import component
from zope import interface

from zope.i18n import translate

from zope.location.interfaces import LocationError

from zope.traversing.interfaces import ITraversable

from ZODB.interfaces import IBroken

from nti.common.property import alias

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import ITitledContent
from nti.dataserver.interfaces import IModeledContent
from nti.dataserver.interfaces import IEnclosedContent
from nti.dataserver.interfaces import ITitledDescribedContent
from nti.dataserver.interfaces import IShareableModeledContent
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.dataserver.users.interfaces import TAG_HIDDEN_IN_UI, ICommunityProfile
from nti.dataserver.users.interfaces import IUserProfileSchemaProvider

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import IExternalObject
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.schema.interfaces import find_most_derived_interface

from .interfaces import IUserSearchPolicy
from .interfaces import IIntIdUserSearchPolicy
from .interfaces import IExternalFieldResource
from .interfaces import IModeratorDealtWithFlag
from .interfaces import IExternalFieldTraversable

@interface.implementer(IExternalObject)
@component.adapter(IEnclosedContent)
class EnclosureExternalObject(object):

	def __init__(self, enclosed):
		self.enclosed = enclosed

	def toExternalObject(self, **kwargs):
		# TODO: I have no idea how best to do this
		return to_external_object(self.enclosed.data, **kwargs)

@component.adapter(IBroken)
@interface.implementer(IExternalObject)
class BrokenExternalObject(object):
	"""
	Renders broken object. This is mostly for (legacy) logging purposes, as the general
	NonExternalizableObject support catches these now.

	TODO: Consider removing this. Is the logging worth it? Alternately, should the
	NonExternalizableObject adapter be at the low level externization package or
	up here?
	"""

	def __init__(self, broken):
		self.broken = broken

	def toExternalObject(self, **kwargs):
		# Broken objects mean there's been a persistence
		# issue. Ok to log it because since its broken, it won't try to call back to us
		logger.debug("Broken object found %s, %s", type(self.broken), self.broken)
		result = { 'Class': 'BrokenObject' }
		return result

# External field updates

@interface.implementer(IExternalFieldResource)
class _DefaultExternalFieldResource(object):

	wrap_value = True

	def __init__(self, key, obj , wrap_value=None):
		self.__name__ = key
		# Initially parent is the object. This may be changed later
		self.__parent__ = obj
		self.context = obj
		if wrap_value is not None:
			self.wrap_value = wrap_value

	resource = alias('context')

@interface.implementer(ITraversable)
class _AbstractExternalFieldTraverser(object):
	"""
	Subclasses may also be registered in the ``fields`` namespace
	as traversers for their particular objects to support legacy
	paths as well as new paths.
	"""

	def __init__(self, context, request=None):
		self.context = context
		self.request = request

	_allowed_fields = ()
	_unwrapped_fields = ()

	def __getitem__(self, key):
		if key not in self._allowed_fields:
			raise KeyError(key)
		return _DefaultExternalFieldResource(key, self.context,
											 wrap_value=(None if key not in self._unwrapped_fields else False))

	def __setitem__(self, key, val):
		raise TypeError()
	def __delitem__(self, key):
		raise TypeError()
	def __len__(self):
		return len(self._allowed_fields)

	def traverse(self, name, further_path):
		try:
			return self[name]
		except LocationError:
			raise
		except KeyError:
			raise LocationError(self.context, name)

@interface.implementer(IExternalFieldTraversable)
@component.adapter(IShareableModeledContent)
class SharedWithExternalFieldTraverser(_AbstractExternalFieldTraverser):

	_allowed_fields = ('sharedWith',)

@interface.implementer(IExternalFieldTraversable)
@component.adapter(ITitledContent)
class TitledExternalFieldTraverser(_AbstractExternalFieldTraverser):

	_allowed_fields = ('title',)

@component.adapter(ITitledDescribedContent)
class TitledDescribedExternalFieldTraverser(TitledExternalFieldTraverser):

	_allowed_fields = TitledExternalFieldTraverser._allowed_fields + ('description',)

# The inheritance tree for IShareable and ITitledDescribed is disjoint,
# so a registration for one or the other of those conflicts.
# This class is a general dispatcher and should be registered for IModeledContent
@component.adapter(IModeledContent)
class GenericModeledContentExternalFieldTraverser(TitledDescribedExternalFieldTraverser,
												  SharedWithExternalFieldTraverser):

	_allowed_fields = 	SharedWithExternalFieldTraverser._allowed_fields + \
						TitledDescribedExternalFieldTraverser._allowed_fields + ('body',)
	_unwrapped_fields = SharedWithExternalFieldTraverser._unwrapped_fields + \
						TitledDescribedExternalFieldTraverser._unwrapped_fields

@component.adapter(IUser)
@interface.implementer(IExternalFieldTraversable)
class UserExternalFieldTraverser(_AbstractExternalFieldTraverser):

	_unwrapped_fields = ('password',)

	def __init__(self, context, request=None):
		super(UserExternalFieldTraverser, self).__init__(context, request=request)
		profile_iface = IUserProfileSchemaProvider(context).getSchema()
		profile = profile_iface(context)
		profile_schema = find_most_derived_interface(profile,
													 profile_iface,
													 possibilities=interface.providedBy(profile))

		allowed_fields = {'lastLoginTime', 'password', 'mute_conversation',
						  'unmute_conversation', 'ignoring', 'accepting',
						  'NotificationCount', 'avatarURL', 'backgroundURL' }

		for k, v in profile_schema.namesAndDescriptions(all=True):
			__traceback_info__ = k, v
			if interface.interfaces.IMethod.providedBy(v):
				continue
			# v could be a schema field or an interface.Attribute
			if v.queryTaggedValue(TAG_HIDDEN_IN_UI):
				continue
			allowed_fields.add(k)

		self._allowed_fields = allowed_fields

@component.adapter(ICommunity)
@interface.implementer(IExternalFieldTraversable)
class CommunityExternalFieldTraverser(_AbstractExternalFieldTraverser):

	_unwrapped_fields = ('password',)

	def __init__(self, context, request=None):
		super(CommunityExternalFieldTraverser, self).__init__(context, request=request)
		allowed_fields = {'avatarURL', 'backgroundURL'}
		for k, v in ICommunityProfile.namesAndDescriptions(all=True):
			__traceback_info__ = k, v
			if interface.interfaces.IMethod.providedBy(v):
				continue
			# v could be a schema field or an interface.Attribute
			if v.queryTaggedValue(TAG_HIDDEN_IN_UI):
				continue
			allowed_fields.add(k)
		self._allowed_fields = allowed_fields

import nameparser
nameparser_config = getattr(nameparser, "config")

from zope.i18n.interfaces import IUserPreferredLanguages

from pyramid.threadlocal import get_current_request

_REALNAME_FIELDS = ('realname', 'NonI18NFirstName', 'NonI18NLastName')

@component.adapter(IUser)
@interface.implementer(IExternalObjectDecorator)
class _UserRealnameStripper(object):
	"""
	At this time, we never, ever, ever, want to send back the extremely valuable and
	privacy sensitive data we have stored in our 'realname' field. It's our secret.

	Except when its not. We have the requirement to do some expensive computations
	every time we echo one of these things back to see if if it might be you. Then we can
	tell you what we think your name is. Even though you cannot edit it. And even though
	it's probably not what you typed in the first place so it will be confusing to you.
	"""
	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		request = get_current_request()
		if request and original.username == request.authenticated_userid:
			return
		for k in _REALNAME_FIELDS:
			if k in external:
				external[k] = None

@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _EnglishFirstAndLastNameDecorator(object):
	"""
	If a user's first preferred language is English,
	then assume that they provided a first and last name and return that
	in the profile data.

	.. note::
		This is an incredibly Western and even US centric way of
		looking at things. The restriction to those that prefer
		English as their language is an attempt to limit the damage.
	"""

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, original, external):
		realname = external.get('realname')
		if not realname or '@' in realname or realname == external.get('ID'):
			return

		preflangs = IUserPreferredLanguages(original, None)
		if preflangs and 'en' == (preflangs.getPreferredLanguages() or (None,))[0]:
			# FIXME: Duplicated from users.user_profile
			# CFA: another suffix we see from certain financial quorters
			suffixes = nameparser_config.SUFFIXES | set(('cfa',))
			constants = nameparser_config.Constants(suffixes=suffixes)

			human_name = nameparser.HumanName(realname, constants=constants)
			first = human_name.first or human_name.last
			last = human_name.last or human_name.first

			if first:
				external['NonI18NFirstName'] = first
				external['NonI18NLastName'] = last

from zope.intid.interfaces import IIntIds

from zope.catalog.interfaces import ICatalog

from nti.dataserver.users.entity import Entity
from nti.dataserver.users import index as user_index

def _make_min_max_btree_range(search_term):
	min_inclusive = search_term  # start here
	# Get all the keys up to the next one that is alphabetically after this
	# one....note because it is a range we need to increment the *last*
	# character in the prefix
	max_exclusive = search_term[0:-1] + unichr(ord(search_term[-1]) + 1)
	return min_inclusive, max_exclusive

def _intids_to_provided(intids, provided, matches):
	# Ok, resolve the intids to actual objects
	id_util = component.getUtility(IIntIds)
	for intid in intids:
		match = id_util.getObject(intid)
		if provided(match):
			matches.add(match)
	return matches

@interface.implementer(IUserSearchPolicy)
class _UsernameSearchPolicy(object):
	"""
	Queries strictly based on the username, doing prefix matching.
	"""

	def __init__(self, context):
		self.context = context

	def do_query_intids(self, search_term, _result=None):
		# XXX: Do we have a username index we can use?
		matching_intid_sets = _result if _result is not None else list()

		matching_objects = self.query(search_term,
									  # No need to pay for hashing/comparisons, just collect
									  _result=list())
		if matching_objects:
			id_util = component.getUtility(IIntIds)
			ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
			id_set = ent_catalog.family.IF.Set()
			for x in matching_objects:
				id_set.add(id_util.getId(x))
			matching_intid_sets.append(id_set)
		return matching_intid_sets

	def query(self, search_term, provided=IEntity.providedBy, _result=None):
		dataserver = component.getUtility(IDataserver)
		_users = IShardLayout(dataserver).users_folder

		result = _result or set()
		# We used to have some nice heuristics about when to include uid-only
		# matches. This became much less valuable when we started to never display
		# anything except uid and sometimes to only want to search on UID:
		# # Searching the userid is generally not what we want
		# # now that we have username and alias (e.g,
		# # tfandango@gmail.com -> Troy Daley. Search for "Dan" and get Troy and
		# # be very confused.). As a compromise, we include them
		# # if there are no other matches
		# Therefore we say screw it and throw that heuristic out the window.
		# It turns out that searching on contains for the UID is not very helpful.
		# Instead, we make it a prefix match, which we can do with
		# btrees: btrees.keys( [min,max) )
		min_inclusive, max_exclusive = _make_min_max_btree_range(search_term)
		__traceback_info__ = _users
		for entity_name in _users.iterkeys(min_inclusive, max_exclusive, excludemax=True):
			__traceback_info__ = entity_name, search_term, min_inclusive, max_exclusive
			# If we did this correct, that's a prefix match
			assert entity_name.lower().startswith(search_term)
			# Even though we could access this directly from the _users
			# container, it's best to go through the Entity class
			# in case it does acquisition wrapping or something
			try:
				entity = Entity.get_entity(entity_name, dataserver=dataserver)
				if entity is not None:
					result.add(entity)
			except KeyError:  # pragma: no cover
				# Typically POSKeyError
				logger.warning("Failed to search entity %s", entity_name)
		return result

@interface.implementer(IUserSearchPolicy)
class _AliasUserSearchPolicy(object):
	"""
	Something that searches on the alias.
	"""

	# : Define here the names of the indexes in the user catalog
	# : to search over. These indexes should be case-normalizing indexes
	# : that store their keys in lower case (as the search term is
	# : provided that way). You must define a matching `_iterindexitems_NAME`
	# : method to determine the keys to get; each key will be treated
	# : as a prefix match, and we assume the prefix match has already
	# : been done.
	_index_names = ('alias',)

	def __init__(self, context):
		self.context = context

	def _iterindexitems_alias(self, search_term, index):
		"""
		Return an iterable of tuples, (matching term, [intids])
		given the search term.

		For alias, it makes sense to only search by prefix (not substring)
		like we do for usernames. This lets us use the same optimization to elide
		keys outside the prefix range.
		"""
		# We can avoid using the _fwd_index by querying the alias
		# index with its intended 'apply' method, except that doesn't let
		# us be specific about excluding the max
		# return ( (search_term, index.apply( _make_min_max_btree_range( search_term ) )), )
		return index._fwd_index.iteritems(*_make_min_max_btree_range(search_term), excludemax=True)

	def do_query_intids(self, search_term, _result=None):
		"""
		Returns a sequence of sets of intids.
		"""
		ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
		# We accumulate intermediate results in their intid format.
		# Although each given object should show up in each index only
		# once, we may be working with multiple indices that all match
		# the same object, and we may have various profile versions
		# around (though we SHOULD NOT have those in the index),
		# when ultimately we only want the entity itself.
		# Building a set of ints is in optimized C code and is much
		# faster than a set of arbitrary objects using python
		# comparisons.
		# Anecdotally, using a single call to multiunion is even faster
		# (according to repoze.catalog) and paves the way to using intid sets
		# through the entire query process
		matching_intid_sets = _result if _result is not None else list()

		for index_name in self._index_names:
			index = ent_catalog[index_name]
			items = getattr(self, '_iterindexitems_' + index_name)(search_term, index)
			for key, intids in items:
				assert key.startswith(search_term)
				# Yes, we like the things for this key. Add the ids of the
				# things mapped to it to our set of matches
				matching_intid_sets.append(intids)
		return matching_intid_sets

	def query(self, search_term, provided=IEntity.providedBy, _result=None):
		matches = _result if _result is not None else set()

		matching_intid_sets = self.do_query_intids(search_term)

		if matching_intid_sets:
			ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
			matching_intids = ent_catalog.family.IF.multiunion(matching_intid_sets)
			matches = _intids_to_provided(matching_intids, provided, matches)
		return matches

@interface.implementer(IUserSearchPolicy)
class _RealnameAliasUserSearchPolicy(_AliasUserSearchPolicy):
	"""
	Something that searches on the realname and alias.
	"""

	_index_names = _AliasUserSearchPolicy._index_names + ('realname_parts',)

	def _iterindexitems_realname_parts(self, search_term, index):
		# For realnames, we want to do a prefix match on each identifiable
		# component.
		#
		# This can be done manually by iterating the realname index keys
		# and splitting each one, but we can also use a keyword index
		# to maintain it for us, which lets us take advantage of prefix
		# ranges (though this is not directly supported in the index
		# interface).
		result = index._fwd_index.iteritems(*_make_min_max_btree_range(search_term),
											excludemax=True)
		return result

@interface.implementer(IIntIdUserSearchPolicy)
class _ComprehensiveUserSearchPolicy(object):
	"""
	Searches on username, plus the profile fields.
	"""

	def __init__(self, context):
		self.context = context
		self._username_policy = _UsernameSearchPolicy(context)
		self._name_policy = _RealnameAliasUserSearchPolicy(context)

	def query_intids(self, search_term):
		intid_sets = list()
		intid_sets = self._username_policy.do_query_intids(search_term, _result=intid_sets)
		intid_sets = self._name_policy.do_query_intids(search_term, _result=intid_sets)
		ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
		if intid_sets:
			return ent_catalog.family.IF.multiunion(intid_sets)
		return ent_catalog.family.IF.Set()

	def query(self, search_term, provided=IEntity.providedBy):
		result = set()
		intids = self.query_intids(search_term)
		if intids:
			result = _intids_to_provided(intids, provided, result)
		return result

@interface.implementer(IUserSearchPolicy)
class _NoOpUserSearchPolicy(object):
	"""
	Does no additional matching beyond username.
	"""
	# Turns out we're a singleton so we can't use
	# ivars
	username_policy = _UsernameSearchPolicy(None)

	def query(self, search_term, provided=None):
		return self.username_policy.query(search_term, provided=provided)

class _NoOpUserSearchPolicyAndRealnameStripper(_NoOpUserSearchPolicy, _UserRealnameStripper):
	"""
	A policy that combines stripping realnames with not searching on them (or aliases, actually,
	so only use this on sites that require the username to be equal to the alias).
	"""

	def decorateExternalObject(self, original, external):
		if external.get('Username'):
			external['alias'] = external['Username']
		super(_NoOpUserSearchPolicyAndRealnameStripper, self).decorateExternalObject(original, external)

from nti.externalization.interfaces import StandardExternalFields

from .link_providers import provide_links

@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _AuthenticatedUserLinkAdder(object):
	"""
	When we decorate an user, if the user is ourself, we want to provide
	the same links that we would at logon time, mostly as a convenience
	to the client.
	"""

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, original, external):
		request = get_current_request()
		if not request:
			return

		userid = request.authenticated_userid
		if not userid or original.username != userid:
			return

		links = list(external.get(StandardExternalFields.LINKS, ()))
		links.extend(provide_links(original, request))

		external[StandardExternalFields.LINKS] = links

@interface.implementer(IExternalObjectDecorator)
@component.adapter(IDeletedObjectPlaceholder)
class _DeletedObjectPlaceholderDecorator(object):
	"""
	Replaces the title, description, and body of deleted objects with I18N strings.
	Cleans up some other data too that we don't want out.
	"""

	_message = _("This item has been deleted.")

	_moderator_message = _("This item has been deleted by the moderator.")

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		request = get_current_request()
		deleted_by_moderator = IModeratorDealtWithFlag.providedBy(original)
		message = translate(self._moderator_message if deleted_by_moderator else self._message, context=request)

		if 'title' in external:
			external['title'] = message
		if 'description' in external:
			external['description'] = message
		if 'body' in external:
			external['body'] = [message]

		if 'tags' in external:
			external['tags'] = ()

		if StandardExternalFields.LINKS in external:
			# These may or may not be rendered at this point
			links = []
			for l in external[StandardExternalFields.LINKS]:
				try:
					rel = l['rel']
				except KeyError:
					rel = l.rel
				if rel in ('replies',):
					# We want to allow access to non-deleted children
					# XXX FIXME This should probably be a per-interface whitelist?
					links.append(l)
			external[StandardExternalFields.LINKS] = links

		# Note that we are still externalizing with the original class and mimetype values;
		# to do otherwise would almost certainly break client assumptions about the type of data the APIs return.
		# But we do expose secondary information about this state:
		external['Deleted'] = True
		if deleted_by_moderator:
			external['DeletedByModerator'] = True
