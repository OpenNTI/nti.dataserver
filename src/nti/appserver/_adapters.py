#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AppSever adpapters.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import interface
from zope import component
from zope.i18n import translate
from zope.location import interfaces as loc_interfaces
from zope.traversing import interfaces as trv_interfaces

import ZODB

from nti.appserver import interfaces as app_interfaces
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import datastructures
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

from nti.utils.schema import find_most_derived_interface
from nti.utils.property import alias

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(nti_interfaces.IEnclosedContent )
class EnclosureExternalObject(object):

	def __init__( self, enclosed ):
		self.enclosed = enclosed

	def toExternalObject( self ):
		# TODO: I have no idea how best to do this
		return datastructures.toExternalObject( self.enclosed.data )

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(ZODB.interfaces.IBroken)
class BrokenExternalObject(object):
	"""
	Renders broken object. This is mostly for (legacy) logging purposes, as the general NonExternalizableObject support
	catches these now.

	TODO: Consider removing this. Is the logging worth it? Alternately, should the NonExternalizableObject
	adapter be at the low level externization package or up here?
	"""

	def __init__( self, broken ):
		self.broken = broken

	def toExternalObject( self ):
		# Broken objects mean there's been a persistence
		# issue. Ok to log it because since its broken, it won't try to call back to us
		logger.debug("Broken object found %s, %s", type(self.broken), self.broken)
		result = { 'Class': 'BrokenObject' }
		return result

## External field updates

@interface.implementer(app_interfaces.IExternalFieldResource)
class _DefaultExternalFieldResource(object):
	wrap_value = True
	def __init__( self, key, obj , wrap_value=None):
		self.__name__ = key
		# Initially parent is the object. This may be changed later
		self.__parent__ = obj
		self.context = obj
		if wrap_value is not None:
			self.wrap_value = wrap_value

	resource = alias('context')

@interface.implementer(trv_interfaces.ITraversable)
class _AbstractExternalFieldTraverser(object):
	"""
	Subclasses may also be registered in the ``fields`` namespace
	as traversers for their particular objects to support legacy
	paths as well as new paths.
	"""

	def __init__( self, context, request=None ):
		self.context = context
		self.request = request

	_allowed_fields = ()
	_unwrapped_fields = ()

	def __getitem__( self, key ):
		if key not in self._allowed_fields:
			raise KeyError( key )
		return _DefaultExternalFieldResource( key, self.context, wrap_value=(None if key not in self._unwrapped_fields else False) )

	def __setitem__( self, key, val ): raise TypeError()
	def __delitem__( self, key ): raise TypeError()
	def __len__( self ): return len( self._allowed_fields )

	def traverse( self, name, further_path ):
		try:
			return self[name]
		except loc_interfaces.LocationError:
			raise
		except KeyError:
			raise loc_interfaces.LocationError( self.context, name )

@interface.implementer(app_interfaces.IExternalFieldTraversable)
@component.adapter(nti_interfaces.IShareableModeledContent)
class SharedWithExternalFieldTraverser(_AbstractExternalFieldTraverser):

	_allowed_fields = ('sharedWith',)

@interface.implementer(app_interfaces.IExternalFieldTraversable)
@component.adapter(nti_interfaces.ITitledContent)
class TitledExternalFieldTraverser(_AbstractExternalFieldTraverser):

	_allowed_fields = ('title', )
	#_unwrapped_fields = ('title', )

@component.adapter(nti_interfaces.ITitledDescribedContent)
class TitledDescribedExternalFieldTraverser(TitledExternalFieldTraverser):

	_allowed_fields = TitledExternalFieldTraverser._allowed_fields + ('description',)
	#_unwrapped_fields = TitledExternalFieldTraverser._unwrapped_fields + ('description',)

# The inheritance tree for IShareable and ITitledDescribed is disjoint,
# so a registration for one or the other of those conflicts.
# This class is a general dispatcher and should be registered for IModeledContent
@component.adapter(nti_interfaces.IModeledContent)
class GenericModeledContentExternalFieldTraverser(TitledDescribedExternalFieldTraverser,SharedWithExternalFieldTraverser):

	_allowed_fields = SharedWithExternalFieldTraverser._allowed_fields + TitledDescribedExternalFieldTraverser._allowed_fields + ('body',)
	_unwrapped_fields = SharedWithExternalFieldTraverser._unwrapped_fields + TitledDescribedExternalFieldTraverser._unwrapped_fields

@interface.implementer(app_interfaces.IExternalFieldTraversable)
@component.adapter(nti_interfaces.IUser)
class UserExternalFieldTraverser(_AbstractExternalFieldTraverser):

	_unwrapped_fields = ('password',)

	def __init__( self, context, request=None ):
		super(UserExternalFieldTraverser,self).__init__( context, request=request )
		profile_iface = user_interfaces.IUserProfileSchemaProvider( context ).getSchema()
		profile = profile_iface( context )
		profile_schema = find_most_derived_interface( profile, profile_iface, possibilities=interface.providedBy(profile) )

		allowed_fields = {'lastLoginTime', 'password', 'mute_conversation', 'unmute_conversation', 'ignoring', 'accepting', 'NotificationCount', 'avatarURL' }

		for k, v in profile_schema.namesAndDescriptions(all=True):
			__traceback_info__ = k, v
			if interface.interfaces.IMethod.providedBy( v ):
				continue
			# v could be a schema field or an interface.Attribute
			if v.queryTaggedValue( user_interfaces.TAG_HIDDEN_IN_UI ):
				continue

			allowed_fields.add( k )

		self._allowed_fields = allowed_fields

from nti.utils import create_gravatar_url


from nti.dataserver.users import DynamicFriendsList

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
@component.adapter(DynamicFriendsList)
class _DFLUserLikeDecorator(object):
	"""
	For purposes of the web UI, cause DFL to use their unique NTIID as the 'username' field.
	"""
	__metaclass__ = SingletonDecorator

	def decorateExternalObject( self, original, external ):
		external['Username'] = original.NTIID
		# The application gets confused. Sometimes it uses the ID,
		# sometimes the Username.
		external['ID'] = original.NTIID


import nameparser
from pyramid import security as psec
from pyramid.threadlocal import get_current_request
from zope.i18n.interfaces import IUserPreferredLanguages

_REALNAME_FIELDS = ('realname', 'NonI18NFirstName', 'NonI18NLastName')

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
@component.adapter(nti_interfaces.IUser)
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

	def decorateExternalObject( self, original, external ):
		if original.username == psec.authenticated_userid( get_current_request() ):
			return
		for k in _REALNAME_FIELDS:
			if k in external:
				external[k] = None


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IUser)
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

	def decorateExternalMapping( self, original, external ):
		realname = external.get( 'realname' )
		if not realname or '@' in realname or realname == external.get( 'ID' ):
			return

		preflangs = IUserPreferredLanguages( original, None )
		if preflangs and 'en' == (preflangs.getPreferredLanguages() or (None,))[0]:
			human_name = nameparser.HumanName( realname )
			first = human_name.first or human_name.last
			last = human_name.last or human_name.first

			if first:
				external['NonI18NFirstName'] = first
				external['NonI18NLastName'] = last


### Localization


@interface.implementer(IUserPreferredLanguages)
@component.adapter(nti_interfaces.IUser)
class _UserPreferredLanguages(object):
	"""
	The preferred languages to use when externalizing for a particular user.

	.. todo:: Right now, this is hardcoded to english. We need to store this.

	"""
	def __init__( self, context ):
		pass

	def getPreferredLanguages(self):
		return ('en',)

# because this is hardcoded, we can be static for now
_user_preferred_languages = _UserPreferredLanguages(None)
@interface.implementer(IUserPreferredLanguages)
@component.adapter(nti_interfaces.IUser)
def UserPreferredLanguages(user):
	return _user_preferred_languages

from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.users import index as user_index
from nti.dataserver.users.entity import Entity
from zope.catalog.interfaces import ICatalog
from zope.intid.interfaces import IIntIds
from nameparser import HumanName

def _make_min_max_btree_range( search_term ):
	min_inclusive = search_term # start here
	# Get all the keys up to the next one that is alphabetically after this
	# one....note because it is a range we need to increment the *last*
	# character in the prefix
	max_exclusive = search_term[0:-1] + unichr(ord(search_term[-1]) + 1)
	return min_inclusive, max_exclusive


@interface.implementer(app_interfaces.IUserSearchPolicy)
class _UsernameSearchPolicy(object):
	"Queries strictly based on the username, doing prefix matching."

	def __init__( self, context ):
		self.context = context

	def query( self, search_term, provided=nti_interfaces.IEntity.providedBy, _result=None ):
		dataserver = component.getUtility(nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout( dataserver ).users_folder

		result = _result or set()
		# We used to have some nice heuristics about when to include uid-only
		# matches. This became much less valuable when we started to never display
		# anything except uid and sometimes to only want to search on UID:
		## Searching the userid is generally not what we want
		## now that we have username and alias (e.g,
		## tfandango@gmail.com -> Troy Daley. Search for "Dan" and get Troy and
		## be very confused.). As a compromise, we include them
		## if there are no other matches
		# Therefore we say screw it and throw that heuristic out the window.
		# It turns out that searching on contains for the UID is not very helpful.
		# Instead, we make it a prefix match, which we can do with
		# btrees: btrees.keys( [min,max) )
		min_inclusive, max_exclusive = _make_min_max_btree_range( search_term )
		__traceback_info__ = _users
		for entity_name in _users.iterkeys(min_inclusive,max_exclusive):
			__traceback_info__ = entity_name, search_term, min_inclusive, max_exclusive
			entity = None
			# If we did this correct, that's a prefix match
			assert entity_name.lower().startswith( search_term )
			# Even though we could access this directly from the _users
			# container, it's best to go through the Entity class
			# in case it does acquisition wrapping or something
			try:
				entity = Entity.get_entity( entity_name, dataserver=dataserver )
			except KeyError: # pragma: no cover
				# Typically POSKeyError
				logger.warning( "Failed to search entity %s", entity_name )

			if entity is not None:
				result.add( entity )

		return result

@interface.implementer(app_interfaces.IUserSearchPolicy)
class _AliasUserSearchPolicy(object):
	"""
	Something that searches on the alias.
	"""

	#: Define here the names of the indexes in the user catalog
	#: to search over. These indexes should be case-normalizing indexes
	#: that store their keys in lower case (as the search term is
	#: provided that way). You must define a matching `_iterindexitems_NAME`
	#: method to determine the keys to get; each key will be treated
	#: as a prefix match, and we assume the prefix match has already
	#: been done.
	_index_names = ('alias',)

	def __init__( self, context ):
		self.context = context

	def _iterindexitems_alias(self, search_term, index):
		"""
		Return an iterable of the index keys we want to check,
		given the search term.

		For alias, it makes sense to only search by prefix (not substring)
		like we do for usernames. This lets us use the same optimization to elide
		keys outside the prefix range.
		"""
		# Each FieldIndex defines a `_fwd_index` private member
		# that is an OOBTree mapping indexed values to docids.
		# In order to know the full set of values in the system, we inspect
		# this index.
		return index._fwd_index.iteritems( *_make_min_max_btree_range( search_term ) )


	def query( self, search_term, provided=nti_interfaces.IEntity.providedBy, _result=None ):
		matches = _result or set()

		ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
		# We accumulate intermediate results in their intid format.
		# Although each given object should show up in each index only
		# once, we may be working with multiple indices that all match
		# the same object, and we may have various profile versions
		# around, when ultimately we only want the entity itself.
		# Building a set of ints is in optimized C code and is much
		# faster than a set of arbitrary objects using python
		# comparisons.
		matching_intids = ent_catalog.family.IF.TreeSet()

		for index_name in self._index_names:
			index = ent_catalog[index_name]
			items = getattr( self, '_iterindexitems_' + index_name )( search_term, index )
			for key, intids in items:
				assert key.startswith(search_term)
				# Yes, we like the things for this key. Add the ids of the
				# things mapped to it to our set of matches
				matching_intids = ent_catalog.family.IF.union( matching_intids, intids )

		if matching_intids:
			# Ok, resolve the intids to actual objects
			id_util = component.getUtility(IIntIds)
			for intid in matching_intids:
				match = id_util.getObject( intid )
				if provided( match ):
					matches.add( match )

		return matches


@interface.implementer(app_interfaces.IUserSearchPolicy)
class _RealnameAliasUserSearchPolicy(_AliasUserSearchPolicy):
	"""
	Something that searches on the realname and alias.
	"""

	_index_names = _AliasUserSearchPolicy._index_names + ('realname',)

	def _iterindexitems_realname(self, search_term, index):
		# For realnames, we want to do a prefix match on each identifiable
		# component.
		# Unfortunately, since we don't index each component separately,
		# this means we must do a complete iteration of the index.
		# We could parse these with nameparser, but probably
		# simply splitting them is good enough
		for basic_name, items in index._fwd_index.iteritems():
			for part in basic_name.split():
				if part and len(part) >= 3 and part.startswith( search_term ):
					yield part, items
					break


@interface.implementer(app_interfaces.IUserSearchPolicy)
class _ComprehensiveUserSearchPolicy(object):
	"""
	Searches on username, plus the profile fields.
	"""

	def __init__( self, context ):
		self.context = context
		self._username_policy = _UsernameSearchPolicy(context)
		self._name_policy = _RealnameAliasUserSearchPolicy(context)

	def query( self, search_term, provided=nti_interfaces.IEntity.providedBy ):
		result = set()
		result = self._username_policy.query( search_term, provided=provided, _result=result )
		result = self._name_policy.query( search_term, provided=provided, _result=result )
		return result

@interface.implementer(app_interfaces.IUserSearchPolicy)
class _NoOpUserSearchPolicy(object):
	"""
	Does no additional matching beyond username.
	"""
	# Turns out we're a singleton so we can't use
	# ivars
	username_policy = _UsernameSearchPolicy(None)

	def query( self, search_term, provided=None ):
		return self.username_policy.query( search_term, provided=provided )

class _NoOpUserSearchPolicyAndRealnameStripper(_NoOpUserSearchPolicy,_UserRealnameStripper):
	"""
	A policy that combines stripping realnames with not searching on them (or aliases, actually,
	so only use this on sites that require the username to be equal to the alias).
	"""

	def decorateExternalObject( self, original, external ):
		if external.get( 'Username' ):
			external['alias'] = external['Username']
		super(_NoOpUserSearchPolicyAndRealnameStripper,self).decorateExternalObject( original, external )

from nti.externalization.interfaces import StandardExternalFields

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IUser)
class _AuthenticatedUserLinkAdder(object):
	"""
	When we decorate an user, if the user is ourself, we want to provide
	the same links that we would at logon time, mostly as a convenience
	to the client.
	"""

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, original, external ):
		request = get_current_request()
		if not request:
			return

		userid = psec.authenticated_userid( request )
		if not userid or original.username != userid:
			return

		links = list( external.get( StandardExternalFields.LINKS, () ) )
		reg = component.getSiteManager() # not pyramid.threadlocal.get_current_registry or request.registry, it ignores the site

		for provider in reg.subscribers( (original,request), app_interfaces.IAuthenticatedUserLinkProvider ):
			links.extend( provider.get_links() )

		external[StandardExternalFields.LINKS] = links

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
@component.adapter(app_interfaces.IDeletedObjectPlaceholder)
class _DeletedObjectPlaceholderDecorator(object):
	"""
	Replaces the title, description, and body of deleted objects with I18N strings.
	Cleans up some other data too that we don't want out.
	"""

	_message = _("This item has been deleted.")

	_moderator_message = _("This item has been deleted by the moderator.")

	__metaclass__ = SingletonDecorator

	def decorateExternalObject( self, original, external ):
		request = get_current_request()
		deleted_by_moderator = app_interfaces.IModeratorDealtWithFlag.providedBy( original )
		message = translate( self._moderator_message if deleted_by_moderator else self._message, context=request )

		if 'title' in external:
			external['title'] = message
		if 'description' in external:
			external['description'] = message
		if 'body' in external:
			external['body'] = [message]

		if 'tags' in external:
			external['tags'] = ()

		if StandardExternalFields.LINKS in external:
			external[StandardExternalFields.LINKS] = [] # because other things may try to append still

		# Note that we are still externalizing with the original class and mimetype values;
		# to do otherwise would almost certainly break client assumptions about the type of data the APIs return.
		# But we do expose secondary information about this state:
		external['Deleted'] = True
		if deleted_by_moderator:
			external['DeletedByModerator'] = True
