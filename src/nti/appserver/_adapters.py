#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

from zope import interface
from zope import component
from zope.location import interfaces as loc_interfaces
from zope.traversing import interfaces as trv_interfaces

import ZODB

from nti.appserver import interfaces as app_interfaces
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import datastructures
from nti.externalization import interfaces as ext_interfaces

from nti.utils.schema import find_most_derived_interface

class EnclosureExternalObject(object):
	interface.implements( ext_interfaces.IExternalObject )
	component.adapts( nti_interfaces.IEnclosedContent )

	def __init__( self, enclosed ):
		self.enclosed = enclosed

	def toExternalObject( self ):
		# TODO: I have no idea how best to do this
		return datastructures.toExternalObject( self.enclosed.data )


class BrokenExternalObject(object):
	"""
	Renders broken object. This is mostly for (legacy) logging purposes, as the general NonExternalizableObject support
	catches these now.

	TODO: Consider removing this. Is the logging worth it? Alternately, should the NonExternalizableObject
	adapter be at the low level externization package or up here?
	"""
	interface.implements( ext_interfaces.IExternalObject )
	component.adapts( ZODB.interfaces.IBroken )

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
		self.resource = obj
		if wrap_value is not None:
			self.wrap_value = wrap_value

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

	def __getitem__( self, key ):
		raise NotImplementedError()

	def traverse( self, name, further_path ):
		try:
			return self[name]
		except KeyError:
			raise loc_interfaces.LocationError( self.context, name )

@interface.implementer(app_interfaces.IExternalFieldTraversable)
@component.adapter(nti_interfaces.IShareableModeledContent)
class SharedWithExternalFieldTraverser(_AbstractExternalFieldTraverser):


	def __getitem__( self, key ):
		if key != 'sharedWith':
			raise KeyError(key)
		return _DefaultExternalFieldResource( key, self.context )


@interface.implementer(app_interfaces.IExternalFieldTraversable)
@component.adapter(nti_interfaces.IUser)
class UserExternalFieldTraverser(_AbstractExternalFieldTraverser):

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


	def __getitem__( self, key ):
		if key not in self._allowed_fields:
			raise KeyError(key)
		return _DefaultExternalFieldResource( key, self.context, wrap_value=(key != "password") )


from nti.utils import create_gravatar_url

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
@component.adapter(nti_interfaces.ISectionInfo)
class _SectionInfoUserLikeDecorator(object):
	"""
	For purposes of the web UI, make SectionInfos, the other things that come back
	from searching, look more like entities.
	"""
	# SectionInfo implements toExternalObject() itself, so the IExternalMappingDecorator
	# is useless
	def __init__( self, context ):
		pass

	def decorateExternalObject( self, original, external ):
		if 'Username' not in external:
			external['Username'] = original.NTIID
		for k in ('realname', 'alias' ):
			if k not in external:
				external[k] = original.Description if original.Description else original.ID
		if 'avatarURL' not in external:
			external['avatarURL'] = create_gravatar_url( original.ID, 'identicon' )

from nti.dataserver.users import DynamicFriendsList

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
@component.adapter(DynamicFriendsList)
class _DFLUserLikeDecorator(object):
	"""
	For purposes of the web UI, cause DFL to use their unique NTIID as the 'username' field.
	"""

	def __init__( self, context ):
		pass

	def decorateExternalObject( self, original, external ):
		external['Username'] = original.NTIID
		# The application gets confused. Sometimes it uses the ID,
		# sometimes the Username.
		external['ID'] = original.NTIID

from nti.dataserver import users
import nameparser
from pyramid import security as psec
from pyramid.threadlocal import get_current_request
from pyramid.threadlocal import get_current_registry
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

	def __init__( self, *args ):
		pass

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

	.. note:: This is an incredibly Western and even US centric
	way of looking at things. The restriction to those that prefer English
	as their language is an attempt to limit the damage.
	"""

	def __init__( self, *args ): pass

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
from zope.catalog.interfaces import ICatalog


@interface.implementer(app_interfaces.IUserSearchPolicy)
class _AliasUserSearchPolicy(object):
	"""
	Something that searches on the alias in addition to the implicitly searched-on
	username.
	"""

	def __init__( self, *args ):
		pass

	_index_names = ('alias',)

	def query( self, search_term, provided=nti_interfaces.IEntity.providedBy ):
		matches = set()
		ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
		for ix in self._index_names:
			_ix = ent_catalog[ix]
			for key in _ix._fwd_index.iterkeys(): # TODO: Private field
				if search_term in key:
					matches.update( (x for x in ent_catalog.searchResults( **{ix: (key,key)} ) if provided( x ) ) )
					# TODO: For the multiple-index case, we could be more efficient by unioning the underlying
					# intid sets before resolving objects. Not sure how much difference that makes
		return matches


@interface.implementer(app_interfaces.IUserSearchPolicy)
class _ComprehensiveUserSearchPolicy(_AliasUserSearchPolicy):
	"""
	Something that searches on the realname and alias in addition to the implicitly searched-on
	username.
	"""

	_index_names = _AliasUserSearchPolicy._index_names + ('realname',)


@interface.implementer(app_interfaces.IUserSearchPolicy)
class _NoOpUserSearchPolicy(object):
	"""
	Does no additional matching.
	"""

	def __init__( self, *args ):
		pass

	def query( self, search_term, provided=None ):
		return ()

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

	def __init__( self, *args ):
		pass

	def decorateExternalMapping( self, original, external ):
		request = get_current_request()
		if not request:
			return

		userid = psec.authenticated_userid( request )
		if not userid or original.username != userid:
			return

		links = list( external.get( StandardExternalFields.LINKS, () ) )
		try:
			reg = request.registry
		except AttributeError:
			reg = get_current_registry() # match pyramid.security.authenticated_userid

		for provider in reg.subscribers( (original,request), app_interfaces.IAuthenticatedUserLinkProvider ):
			links.extend( provider.get_links() )

		external[StandardExternalFields.LINKS] = links
