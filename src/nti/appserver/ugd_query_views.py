#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for querying user generated data.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"
import logging
logger = logging.getLogger(__name__)

import sys
from numbers import Number
import functools
import itertools
import heapq

from zope import interface
from zope import component
from zope.intid.interfaces import IIntIds

from pyramid.view import view_config
from pyramid import security as psec


from nti.appserver import httpexceptions as hexc
from nti.appserver import _util
from nti.appserver import _view_utils
from nti.appserver._view_utils import get_remote_user
from nti.appserver.pyramid_authorization import is_readable
from nti.appserver.interfaces import IUGDExternalCollection

from nti.contentlibrary import interfaces as lib_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import LocatedExternalDict

from nti.externalization.externalization import to_standard_external_last_modified_time
from nti.externalization.externalization import to_standard_external_created_time
from nti.externalization.oids import to_external_ntiid_oid

from nti.ntiids import ntiids

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.sharing import SharingContextCache
from nti.dataserver import users
from nti.dataserver.users import entity
from nti.dataserver import liking
liking_like_count = liking.like_count # minor optimization
from nti.dataserver import authorization as nauth
from nti.dataserver.mimetype import nti_mimetype_from_object, nti_mimetype_with_class
from nti.dataserver.links import Link

from z3c.batching.batch import Batch

#from perfmetrics import metricmethod


def _TRUE(x): return True

def _lists_and_dicts_to_iterables( lists_and_dicts ):
	result = []

	lists_and_dicts = [item for item in lists_and_dicts if item is not None]
	lastMod = 0
	for list_or_dict in lists_and_dicts:
		try:
			lastMod = max( lastMod, list_or_dict.lastModified )
		except AttributeError:
			pass
		# about half of these will be lists, half dicts. sigh.
		try:
			# ModDateTrackingOOBTrees tend to lose the custom
			# 'lastModified' attribute during persistence
			# so if there is a 'Last Modified' entry, go
			# for that
			to_iter = list_or_dict.itervalues()
			lastMod = max( lastMod, list_or_dict.get( 'Last Modified', 0 ) )
		except (AttributeError,TypeError):
			# then it must be a 'list'
			to_iter = list_or_dict

		result.append( to_iter )
	return result, lastMod

def _iterables_to_filtered_iterables( iterables, predicate ):
	if predicate is _TRUE:
		return iterables
	return [itertools.ifilter( predicate, x ) for x in iterables]

def _lists_and_dicts_to_ext_iterables( lists_and_dicts,
									   predicate=_TRUE,
									   result_iface=IUGDExternalCollection,
									   ignore_broken=False,
									   pre_filtered=False):
	"""
	Given items that may be dictionaries or lists, combines them
	and externalizes them for return to the user as a dictionary.

	If the individual items are ModDateTracking (have a
	lastModified value) then the returned dict will have the maximum
	value as 'Last Modified'.

	:param callable predicate: Objects will only make it into the final 'Items' list
		if this function returns true for all of them. Defaults to a True filter.
	"""
	result = LocatedExternalDict()

	# To avoid returning duplicates, we keep track of object
	# ids and only add one copy. We used to use the external_oid, but that's
	# needlessly complicated: anything with an oid is guaranteed to be in memory
	# just once (from a particular transaction) and thus has a unique id
	# We also reject None and numbers
	oids = set()

	def _base_predicate(x):
		if x is None or isinstance(x, Number):
			return False
		#try:
			#oid = to_external_oid( x, str( id(x) ) )
			#oid = getattr( x, '_p_oid', id(x) )
		#except POSKeyError:
		#	if ignore_broken:
		#		return False
		#	raise
		oid = id(x)
		if oid in oids:
			# avoid dups. This check is slightly less expensive than
			# some predicates (is_readable) so do it first
			return False
		oids.add( oid )
		# TODO: This may not be right, if we're going to filter
		# this object out with a subsequent predicate?
		# It also results in loading the state for all these objects,
		# even if we are going to filter them out, which is not good either
		# (If the predicates are carefully arranged that might not be needed)
		#try:
		#	result.lastModified = max(result.lastModified, x.lastModified)
		#except AttributeError:
		#	pass
		return True

	if pre_filtered:
		_predicate = _TRUE
	elif predicate is _TRUE or predicate is None:
		_predicate = _base_predicate
	else:
		_predicate = lambda x: _base_predicate(x) and predicate(x)


	iterables, result.lastModified = _lists_and_dicts_to_iterables( lists_and_dicts )
	iterables = _iterables_to_filtered_iterables( iterables, _predicate )

	result['Iterables'] = iterables
	result['Last Modified'] = result.lastModified
	result.mimeType = nti_mimetype_with_class( None )
	interface.alsoProvides( result, result_iface )
	return result

def lists_and_dicts_to_ext_collection( lists_and_dicts, predicate=_TRUE, result_iface=IUGDExternalCollection, ignore_broken=False ):
	""" Given items that may be dictionaries or lists, combines them
	and externalizes them for return to the user as a dictionary. If the individual items
	are ModDateTracking (have a lastModified value) then the returned
	dict will have the maximum value as 'Last Modified'

	:param callable predicate: Objects will only make it into the final 'Items' list
		if this function returns true for all of them. Defaults to a True filter.
	"""
	result = _lists_and_dicts_to_ext_iterables( lists_and_dicts, predicate, result_iface, ignore_broken )
	items = []

	for to_iter in result['Iterables']:
		items.extend( to_iter )

	result['Items'] = items
	del result['Iterables']
	result['Last Modified'] = result.lastModified
	return result


def _reference_list_length( x ):
	try:
		return len(x.referents)
	except AttributeError:
		return -1 # distinguish no refs vs no data

def _reference_list_objects( x ):
	try:
		return x.referents
	except AttributeError:
		return ()

def _reference_list_recursive_like_count( proxy ):
	# There is probably not much use in caching this? It's just a simple sum
	# across a list and everything should be in memory after the first time?
	return sum( (liking_like_count( x ) for x in _reference_list_objects( proxy ) ),
				liking_like_count( proxy ))

def _reference_list_recursive_max_last_modified( proxy ):
	try:
		return max( _reference_list_objects( proxy ), key=to_standard_external_last_modified_time )
	except ValueError: #Empty list
		return 0

def _combine_predicate( new, old ):
	if not old:
		return new
	return lambda obj: new(obj) and old(obj)

def _ifollow_predicate_factory( request, and_me=False, expand_nested=True ):
	me = get_remote_user(request) # the 'I' means the current user, not the one whose date we look at (not  request.context.user)
	following_usernames = set()
	if and_me:
		following_usernames.add( me.username )
	for entity in me.entities_followed:
		entity_username = getattr( entity, 'username', None )
		if entity_username:
			following_usernames.add( entity_username )
		if expand_nested:
			# Expand things that should be expanded, such as DFLs
			for nested_username in nti_interfaces.IUsernameIterable(entity, ()):
				following_usernames.add( nested_username )

	return lambda o: getattr( o.creator, 'username', o.creator ) in following_usernames

def _ifollowandme_predicate_factory( request ):
	return _ifollow_predicate_factory( request, True )

def _favorite_predicate_factory( request ):
	auth_userid = psec.authenticated_userid( request )
	return functools.partial( liking.favorites_object, username=auth_userid, safe=True )

def _bookmark_predicate_factory( request ):
	is_fav_p = _favorite_predicate_factory(request)
	is_bm_p = nti_interfaces.IBookmark.providedBy
	return lambda o: is_fav_p( o ) or is_bm_p( o )

def _toplevel_filter( x ):
	# This won't work for the Change objects. (Try Acquisition?) Do we need it for them?
	try:
		return x.getInReplyTo( allow_cached=False ) is None
	except AttributeError:
		return True # No getInReplyTo means it cannot be a reply, means its toplevel

SORT_KEYS = {
	# LastModified and createdTime are sorted on the same values we would provide
	# externally, which might involve an attribute /or/ adapting to IDCTimes.
	# TODO: As such, these aren't particularly cheap
	'lastModified': functools.partial( to_standard_external_last_modified_time, default=0 ),
	'createdTime' : functools.partial( to_standard_external_created_time, default=0),
	'LikeCount': liking_like_count,
	'ReferencedByCount':  _reference_list_length,
	'RecursiveLikeCount':  _reference_list_recursive_like_count,
	}
SORT_KEYS['CreatedTime'] = SORT_KEYS['createdTime'] # Despite documentation, some clients send this value
SORT_DIRECTION_DEFAULT = {
	'LikeCount': 'descending',
	'ReferencedByCount': 'descending',
	'RecursiveLikeCount': 'descending',
	'lastModified': 'descending'
	}
FILTER_NAMES = {
	'TopLevel': _toplevel_filter,
	'IFollow': (_ifollow_predicate_factory,),
	'IFollowAndMe': (_ifollowandme_predicate_factory,),
	'Favorite': (_favorite_predicate_factory,),
	'Bookmarks': (_bookmark_predicate_factory,),
	}

class _MimeFilter(object):

	def __init__( self, accept_types ):
		self.accept_types = accept_types
		self._accept_classes = ()
		self._exclude_classes = ()

	def _object( self, o ):
		return o

	def _mimetype_from_object( self, o ):
		return nti_mimetype_from_object( o )

	def __call__( self, o ):
		o = self._object(o)
		if o is None:
			return False

		# Be careful to cache exact leaf classes only.
		# The alternative, matching trees (subclasses) is useful,
		# but sometimes confusing.
		# TODO: If we make a further assumption that each mimetype
		# maps one-to-one to a leaf class (which is currently the case, Mar13),
		# then we could query the ZCA factories to find matching mimetypes
		# at creation time and save the cache building...if the types are creatable
		# externally
		o_type = o.__class__ # for proxies, use __class__, not type
		if o_type in self._accept_classes:
			return True
		if o_type in self._exclude_classes:
			return False

		if self._mimetype_from_object(o) in self.accept_types:
			self._accept_classes += (o_type,)
			return True
		self._exclude_classes += (o_type,)
		return False

###
# XXX Hack in some faster-than-full-ACL support to determine
# readability during views

def _created_xxx_isReadableByAnyIdOfUser( self, user, ids, family ):
	return user == self.creator

from nti.assessment.assessed import QAssessedQuestionSet
QAssessedQuestionSet.xxx_isReadableByAnyIdOfUser = _created_xxx_isReadableByAnyIdOfUser
from nti.dataserver.chat_transcripts import _AbstractMeetingTranscriptStorage
_AbstractMeetingTranscriptStorage.xxx_isReadableByAnyIdOfUser = _created_xxx_isReadableByAnyIdOfUser
from nti.dataserver.traversal import find_interface
def _personalblogcomment_xxx_isReadableByAnyIdOfUser( self, user, ids, family ):
	# XXX Duplicates much of the ACL logic
	if user == self.creator:
		return True
	if self.isSharedWith( user ):
		return True
	if find_interface( self, nti_interfaces.IUser, strict=False ) == user:
		return True
from nti.dataserver.contenttypes.forums.post import PersonalBlogComment
PersonalBlogComment.xxx_isReadableByAnyIdOfUser = _personalblogcomment_xxx_isReadableByAnyIdOfUser

def _communityforum_xxx_isReadableByAnyIdOfUser( self, user, ids, family ):
	return self.creator in user.dynamic_memberships
from nti.dataserver.contenttypes.forums.forum import CommunityForum
CommunityForum.xxx_isReadableByAnyIdOfUser = _communityforum_xxx_isReadableByAnyIdOfUser

class _UGDView(_view_utils.AbstractAuthenticatedView):
	"""
	The base view for user generated data.
	"""

	#: The returned list of items will implement this interface.
	result_iface = IUGDExternalCollection

	FILTER_NAMES = FILTER_NAMES
	SORT_DIRECTION_DEFAULT = SORT_DIRECTION_DEFAULT
	SORT_KEYS = SORT_KEYS

	get_owned = users.User.getContainer
	get_shared = users.User.getSharedContainer
	#get_public = None

	_my_objects_may_be_empty = True
	_support_cross_user = True
	#: Ordinarily, when we support cross user queries we don't look
	#: in data shared with the cross user (because it may not be visible to the
	#: remote user)
	_force_shared_objects = False
	_force_apply_security = False

	#: Set this to false, either dynamically or at the class level,
	#: if _sort_filter_batch_objects does not need to do any sort of further
	#: filtering: not the value from _make_complete_predicate, nor
	#: filtering of duplicates or numbers.
	_needs_filtered = True

	ignore_broken = True

	#: The user object whose data we are requesting. This is not
	#: necessarily the same as the authenticated remote user;
	#: additional restrictions apply in that case
	user = None
	#: The NTIID of the container whose data we are requesting
	ntiid = None

	def __init__( self, request, the_user=None, the_ntiid=None ):
		super(_UGDView,self).__init__( request )
		if self.request.context:
			self.user = the_user or self.request.context.user
			self.ntiid = the_ntiid or self.request.context.ntiid
		self.context_cache = SharingContextCache()

	def check_cross_user( self ):
		if not self._support_cross_user:
			if self.user != self.remoteUser:
				raise hexc.HTTPForbidden()

	def __call__( self ):
		self.check_cross_user()
		# pre-flight the batch
		self._get_batch_size_start()

		user, ntiid = self.user, self.ntiid
		the_objects = self.getObjectsForId( user, ntiid )

		result = self._sort_filter_batch_objects( the_objects )
		result.__parent__ = self.request.context
		result.__name__ = ntiid
		result.__data_owner__ = user
		if self.request.method == 'HEAD':
			result['Items'] = () # avoid externalization
		return result

	def __get_list_param( self, name ):
		param = self.request.params.get( name, '' )
		if param:
			return param.split( ',' )
		return []

	def _get_filter_names(self):
		return self.__get_list_param( 'filter' )

	def _get_accept_types(self):
		return self.__get_list_param( 'accept' )

	def _get_exclude_types(self):
		return self.__get_list_param( 'exclude' )

	def _get_shared_with_names(self):
		return self.__get_list_param( 'sharedWith')

	def _get_shared_with( self ):
		names = self._get_shared_with_names()
		entities = []
		for name in names:
			ent = entity.Entity.get_entity( name )
			if ent is not None:
				# TODO: Should there be an access check here?
				entities.append( ent )
		return entities

	def _get_batch_size_start( self ):
		"""
		Return a two-tuple, (batch_size, batch_start). If the values are
		invalid, raises an HTTP exception. If either is missing, returns
		the defaults for both.
		"""

		batch_size = self.request.params.get( 'batchSize', self._DEFAULT_BATCH_SIZE )
		batch_start = self.request.params.get( 'batchStart', self._DEFAULT_BATCH_START )
		if batch_size is not None and batch_start is not None:
			try:
				batch_size = int(batch_size)
				batch_start = int(batch_start)
			except ValueError:
				raise hexc.HTTPBadRequest()
			if batch_size <= 0 or batch_start < 0:
				raise hexc.HTTPBadRequest()

			return batch_size, batch_start

		return self._DEFAULT_BATCH_SIZE, self._DEFAULT_BATCH_START

	@classmethod
	def do_getObjects( cls, owner, containerId, remote_user,
					   get_owned=users.User.getContainer,
					   get_shared=users.User.getSharedContainer,
					   allow_empty=True, context_cache=None ):
		"""
		Returns a sequence of values that can be passed to
		:func:`lists_and_dicts_to_ext_collection`.

		:raises nti.appserver.httpexceptions.HTTPNotFound: If no actual objects can be found.
		"""

		__traceback_info__ = owner, containerId
		mystuffDict = get_owned( owner, containerId, context_cache=context_cache ) if get_owned else ()
		sharedstuffList = get_shared( owner, containerId, context_cache=context_cache) if get_shared else () # see comments in _meonly_predicate_factory

		# To determine the existence of the container,
		# My stuff either exists or it doesn't. The others, being shared,
		# may be empty or not empty.
		if (mystuffDict is None \
			or (not allow_empty and not mystuffDict)) \
			   and not sharedstuffList:

			raise hexc.HTTPNotFound(containerId)

		return (mystuffDict, sharedstuffList, ()) # Last value is placeholder for get_public, currently not used

	def getObjectsForId( self, user, ntiid ):
		"""
		Returns a sequence of values that can be passed to
		:func:`lists_and_dicts_to_ext_collection`.

		:raises nti.appserver.httpexceptions.HTTPNotFound: If no actual objects can be found.
		"""

		remote_user = self.remoteUser
		get_shared = None
		if self._force_shared_objects or (user == remote_user and 'MeOnly' not in self._get_filter_names()):
			# Only consider the shared stuff when the actual user is asking
			# TODO: Handle this better with ACLs
			get_shared = self.get_shared

		return self.do_getObjects( user, ntiid, remote_user,
								   get_owned=self.get_owned,
								   get_shared=get_shared,
								   allow_empty=self._my_objects_may_be_empty,
								   context_cache=self.context_cache)

	_DEFAULT_SORT_ON = 'lastModified'
	_DEFAULT_BATCH_SIZE = None
	_DEFAULT_BATCH_START = None
	_MIME_FILTER_FACTORY = _MimeFilter

	def _make_accept_predicate( self ):
		accept_types = self._get_accept_types()
		if accept_types and '*/*' not in accept_types:
			return self._MIME_FILTER_FACTORY( accept_types )

	def _make_exclude_predicate( self ):
		exclude_types = self._get_exclude_types()
		if exclude_types and '*/*' not in exclude_types:
			mime_filter = self._MIME_FILTER_FACTORY( exclude_types )
			return lambda o: not mime_filter(o)

	def _make_complete_predicate( self ):
		"A predicate for all the filtering, excluding security"

		predicate = None # We build an uber predicate that handles all filtering in one pass through the list
		predicate = self._make_accept_predicate( )
		if predicate is None:
			# accept takes priority over exclude
			predicate = self._make_exclude_predicate()

		filter_names = self._get_filter_names()

		for filter_name in filter_names:
			if filter_name not in self.FILTER_NAMES:
				continue
			the_filter = self.FILTER_NAMES[filter_name]
			if isinstance( the_filter, tuple ):
				the_filter = the_filter[0]( self.request )

			predicate = _combine_predicate( the_filter, predicate )

		shared_with_values = self._get_shared_with()
		if shared_with_values:
			def filter_shared_with( x ):
				x_sharedWith = getattr( x, 'sharedWith', ())
				for shared_with_value in shared_with_values:
					if shared_with_value in x_sharedWith:
						return True
			predicate = _combine_predicate( filter_shared_with, predicate )

		return predicate

	def _make_sort_key_function(self):
		"Returns a key function for sorting based on current params"
		# The request keys match what z3c.table does
		sort_on = self.request.params.get( 'sortOn', self._DEFAULT_SORT_ON )
		_sort_key_function = self.SORT_KEYS.get( sort_on, self.SORT_KEYS[self._DEFAULT_SORT_ON] )
		# If they send a sortOn we don't understand, also do not respect their order parameter,
		# to make the mistake more obvious; sort exactly as if they had sent neither
		if _sort_key_function is self.SORT_KEYS[self._DEFAULT_SORT_ON] and sort_on != self._DEFAULT_SORT_ON:
			sort_on = self._DEFAULT_SORT_ON

		sort_order = self.request.params.get( 'sortOrder', self.SORT_DIRECTION_DEFAULT.get( sort_on, 'ascending' ) )

		# heapq needs to have the smallest item first. It doesn't work with reverse sorting.
		# so in that case we invert the key function
		if sort_order == 'descending':
			def sort_key_function(x):
				return -(_sort_key_function(x))
		else:
			sort_key_function = _sort_key_function
		return sort_key_function


	def _sort_filter_batch_objects( self, objects ):
		"""
		Sort, filter, and batch (page) the objects collections,
		returning a result dictionary. This method sorts by
		``lastModified`` by default, but everything else comes from
		the following query parameters:

		sortOn
			The field to sort on. Options are ``lastModified``,
			``createdTime``, ``LikeCount``, ``RecursiveLikeCount``, and ``ReferencedByCount``.
			Only ``lastModified``, ``createdTime`` are valid for the
			stream views.

		sortOrder
			The sort direction. Options are ``ascending`` and
			``descending``. If you do not specify, a value that makes
			the most sense for the ``sortOn`` parameter will be used
			by default.

		filter
			Whether to filter the returned data in some fashion. Several values are defined:

			* ``TopLevel``: it causes only objects that are not replies to something else
			  to be returned (this is meaningless on the stream views).

			* ``MeOnly``: it causes only things that I have done to be included.

			* ``IFollow``: it causes only things done (created) by people I am directly following
			  to be returned (right now, adding to a FriendsList also defaults to establishing
			  the following relationship, so you can think of this as "My Contacts"). If I am following
			  a dynamic sharing target that provides an iterable list of members (such as a
			  :class:`~nti.dataserver.interfaces.IDynamicSharingTargetFriendsList`), then those members are
			  included as people I am following.
			  Note that this *does not* imply or include things that I have done. This is very efficient.

			* ``IFollowAndMe``: Just like ``IFollow``, but also adds things that I have done.
			  Again, this is very efficient.

			* ``Favorite``: it causes only objects that the current user has
			  :mod:`favorited <nti.appserver.liking_views>` the object to be returned.
			  (Does not function on the stream views.) Currently, this is not especially
			  efficient.

			* ``Bookmarks``: a high-level, pseudo-object filter that causes only
			  objects identified as "bookmarks" to be returned. For this purpose, bookmarks
			  are defined as favorite objects (like with ``Favorite``) with the addition of
			  actual :class:`~nti.dataserver.interfaces.IBookmark` objects. Typically this
			  will not be used together with an ``accept`` parameter or any other ``filter``
			  value.

			They can be combined by separating them with a comma. Note that ``MeOnly`` and
			``IFollow`` are mutually exclusive and specifying them both will result in
			empty results. It is also probably the case that ``MeOnly`` and ``Favorite`` are
			logically mutually exclusive (users probably don't favorite their own objects).

		accept
			A comma-separated list of MIME types of objects to return.
			If not given or ``*/*`` is in the list, all types of
			objects are returned. By default, all types of objects are
			returned. For the stream views, this filters the underlying
			object type that the change references.

		exclude
			A comma-separated list of MIME types of objects *not* to
			return, functioning otherwise like ``accept.`` If
			``accept`` is given (and doesn't contain ``*/*``), any
			value for ``exclude`` is ignored. This value should not
			include ``*/*``.

		sharedWith
			A comma-separated list of usernames specifying who
			returned objects must be shared with (in an `OR` fashion).
			Most commonly used to match a single
			:class:`~nti.dataserver.interfaces.IDynamicSharingTargetFriendsList`
			by sending a single NTIID. The behaviour of specifying
			non-existant or non-accessible usernames is undefined (but
			probably not good).

		batchSize
			Integer giving the page size. Must be greater than zero.
			Paging only happens when this is supplied together with
			``batchStart`` (or ``batchAround`` for those views that support it).

		batchStart
			Integer giving the index of the first object to return,
			starting with zero. Paging only happens when this is
			supplied together with ``batchSize``.

		batchAround
			String parameter giving the ``OID`` of an object to build a batch (page)
			around. When you give this parameter, ``batchStart`` is ignored and
			the found object is centered at one-half the ``batchSize`` in the returned
			page (assuming there are enough following objects). If the object is not
			found (after all the filters are applied) then an empty batch is returned.
			(Even if you supply this value, you should still supply a value for ``batchStart``
			such as 1).

		:param dict result: The result dictionary that will be returned to the client.
			Contains the ``Items`` list of all items found. You may add keys to the dictionary.
			You may (and should) modify the Items list directly.

			This method adds the ``TotalItemCount`` and
			``FilteredTotalItemCount`` keys, containing integers
			giving the total number of results, and the total number
			of filtered results (which is the same as the total if the
			null filter is in use).

			It also ensures that, if batching (paging) is being used,
			if there is a next or previous page, then links of
			relevance ``batch-next`` and ``batch-prev`` are added. You
			should use these links to know when to continue paging
			forward or backwards through the data (as, for example, the very last
			page will have no ``batch-next`` link), rather than trying to construct URLs based
			on the values in ``TotalItemCount`` or ``FilteredTotalItemCount``.

		"""
		needs_security = self._force_apply_security or self.remoteUser != self.user

		# Our security check is optimized for sharing objects, not taking the full
		# ACL into account.
		if not needs_security:
			def security_check(x):
				return True
			tuple_security_check = security_check
		else:
			remote_user = self.remoteUser
			my_ids = self.remoteUser.xxx_intids_of_memberships_and_self
			family = component.getUtility( IIntIds ).family
			def security_check(x):
				try:
					if remote_user == x.creator:
						return True
				except AttributeError:
					pass
				try:
					return x.xxx_isReadableByAnyIdOfUser( remote_user, my_ids, family )
				except (AttributeError,TypeError) as e:
					try:
						return x.isSharedWith( remote_user ) # TODO: Might need to OR this with is_readable?
					except AttributeError as e:
						return is_readable(x)
			def tuple_security_check(x):
				return security_check(x[1])

		total_item_count = sum( (len(x) for x in objects if x is not None) )

		pre_filtered = not self._needs_filtered
		predicate = self._make_complete_predicate()
		sort_key_function = self._make_sort_key_function()
		batch_size, batch_start = self._get_batch_size_start()

		number_items_needed = total_item_count
		if batch_size is not None and batch_start is not None:
			number_items_needed = min(batch_size + batch_start + 2, total_item_count)

		# First, take the cheap, non-secure filter to all the subobjects
		result = _lists_and_dicts_to_ext_iterables( objects,
													predicate=predicate,
													result_iface=self.result_iface,
													ignore_broken=self.ignore_broken,
													pre_filtered=pre_filtered)
		iterables = result['Iterables']
		del result['Iterables']

		result['TotalItemCount'] = total_item_count

		# Now, sort each subset.
		# Sorting all the small subsets is faster than sorting one huge list and potentially
		# easier to cache---if there are relatively many items, compared to the number of sublists;
		# otherwise it is faster to combine once and then sort. (TODO: Prove this algorithmically)
		if total_item_count < len(iterables) * 4 or total_item_count < 5000: # XXX Magic number
			iterables = [itertools.chain(*iterables)]
		#  This assumes we are going to want to page
		# These are reified.
		heap_key = lambda x: (sort_key_function(x), x)
		sortable_iterables = [itertools.imap(heap_key, x) for x in iterables]
		if number_items_needed < total_item_count and number_items_needed < 500: # Works best for "small values"
			# If we can get away with just partially sorting the iterables,
			# because we're paging, do it
			# TODO: This is experimental. By doing this, we have fewer total objects
			# and smaller lists in memory at once. But the consequence is that our
			# permission check gets done on every object, which may be the bottleneck
			# NOTE: At least in alpha, this is the bottleneck. we're better off pulling the filtered
			# list in to memory
			_USE_SMALLEST = False
			if _USE_SMALLEST:
				if needs_security:
					sortable_iterables = [itertools.ifilter( tuple_security_check, x ) for x in sortable_iterables]
					needs_security = False
				sorted_sublists = [heapq.nsmallest( number_items_needed, x ) for x in sortable_iterables]
			else:
				sorted_sublists = [sorted(x, key=lambda x: x[0]) for x in sortable_iterables]
		else:
			# Note that we are already computing the key once, no need to include the other
			# object in the comparison
			sorted_sublists = [sorted(x, key=lambda x: x[0]) for x in sortable_iterables]

		result['Last Modified'] = result.lastModified

		result['FilteredTotalItemCount'] = sum( (len(x) for x in sorted_sublists) ) # this may be an approximation


		# Apply cross-user security if needed
		# Do this after all the filtering because it's the most expensive
		# filter of all
		if needs_security:
			sorted_sublists = [itertools.ifilter( tuple_security_check, x ) for x in sorted_sublists]


		# Now merge the lists altogether if we didn't already
		# `merged` will be an iterable of the sorted tuples: (key, value)
		if len(sorted_sublists) > 1:
			merged = heapq.merge( *sorted_sublists )
		elif sorted_sublists:
			merged = sorted_sublists[0]
		else:
			merged = ()

		batch_size, batch_start = self._get_batch_size_start()
		if self.request.params.get( 'batchAround', '' ) and batch_size is not None:
			batchAround = self.request.params.get( 'batchAround' )
			# Ok, they have requested that we compute a beginning index for them.
			# We do this by materializing the list in memory and walking through
			# to find the index of the requested object.
			batch_start = None
			result_list = []
			for i, key_value in enumerate(merged):
				# Only keep testing until we find what we need
				if batch_start is None:
					if to_external_ntiid_oid( key_value[1] ) == batchAround:
						batch_start = max( 1, i - (batch_size // 2) - 1 )
				result_list.append( key_value )
			merged = result_list
			if batch_start is None:
				# Well, we got here without finding the matching value.
				# So return an empty page.
				batch_start = len(result_list)

		if batch_size is not None and batch_start is not None:
			# Ok, reify up to batch_size + batch_start + 2 items from merged
			result_list = []
			count = 0
			for _, x in merged:
				result_list.append( x )
				count += 1
				if count > number_items_needed:
					break

			if batch_start >= len(result_list):
				# Batch raises IndexError
				result_list = []
			else:
				result_list = Batch( result_list, batch_start, batch_size )
				# Insert links to the next and previous batch
				# NOTE: If our batch_start is not a multiple of the batch_size,
				# we may not get a previous (if there are fewer than batch_size previous elements?)
				# Also in that case, our next may be set up to reach the end of the data, overlapping this
				# one if need be.
				next_batch, prev_batch = result_list.next, result_list.previous
				for batch, rel in ((next_batch, 'batch-next'), (prev_batch, 'batch-prev')):
					if batch is not None and batch != result_list:
						batch_params = self.request.params.copy()
						# Pop some things that don't work
						batch_params.pop( 'batchAround', '' )
						# TODO: batchBefore
						batch_params['batchStart'] = batch.start
						link_next_href = self.request.current_route_path( _query=sorted(batch_params.items()) ) # sort for reliable testing
						link_next = Link( link_next_href, rel=rel )
						result.setdefault( 'Links', [] ).append( link_next )

			result['Items'] = result_list
		else:
			# Not batching.
			result_list = [x[1] for x in merged]
			result['Items'] = result_list


		return result

class _RecursiveUGDView(_UGDView):
	"""
	Just like a normal :class:`._UGDView`, but recurses through all the NTIID
	containers beneath the given NTIID. The unnamed container is always included.
	If the :data:`.ntiids.ROOT` is given, then all NTIID containers of the user
	are examined (the hierarchy is effectively ignored).
	"""

	_iter_ntiids_stream_only = False
	_iter_ntiids_include_stream = True

	def _get_filter_names( self ):
		"""
		Special case some things to account for some interesting patterns the app has.

		#. There is a tab where it sends an accept for transcript summaries. These are only
		   ever found for the current user, so we can be sure to add 'MeOnly' to the filters
		   in that case.
		"""
		filters = super(_RecursiveUGDView,self)._get_filter_names()
		if self._get_accept_types() == ['application/vnd.nextthought.transcriptsummary']: # equals, not contains
			filters = set(filters)
			filters.add( 'MeOnly' )
		return filters

	def _get_containerids_for_id( self, user, ntiid ):
		containers = ()
		if ntiid == ntiids.ROOT:
			containers = set(user.iterntiids(include_stream=self._iter_ntiids_include_stream,stream_only=self._iter_ntiids_stream_only))
		else:
			library = self.request.registry.getUtility( lib_interfaces.IContentPackageLibrary )
			tocEntries = library.childrenOfNTIID( ntiid )

			containers = {toc.ntiid for toc in tocEntries} # children
			containers.add( ntiid ) # item

		# We always include the unnamed root (which holds things like CIRCLED)
		# NOTE: This is only in the stream. Normally we cannot store contained
		# objects with an empty container key, so this takes internal magic
		containers.add( '' ) # root

		return containers

	def getObjectsForId( self, user, ntiid ):
		containers = self._get_containerids_for_id( user, ntiid )
		exc_info = None
		items = []
		for container in containers:
			try:
				items.extend( super(_RecursiveUGDView,self).getObjectsForId( user, container ) )
			except hexc.HTTPNotFound:
				exc_info = sys.exc_info()

		items = [x for x in items if x is not None] # TODO: Who gives us back a None? Seen on the Root with MeOnly filter
		self._check_for_not_found( items, exc_info )
		return items

	def _check_for_not_found( self, items, exc_info ):
		# We are not found iff the root container DNE (empty is OK)
		# and the children are empty/DNE. In other words, if
		# accessing UGD for this container would throw,
		# so does accessing recursive.
		empty = len(items) == 0
		if not empty:
			# We have items. We are only truly empty, though,
			# if each and every one of the items is empty.
			empty = True
			for i in items:
				if not i:
					continue # Avoid possibly expensive length computation for usually cheaper bool check
				li = len(i)
				if li >= 2 or (li == 1 and 'Last Modified' not in i):
					empty = False
					break

		if empty and exc_info:
			# Throw the previous not found exception.
			raise exc_info[0], exc_info[1], exc_info[2]



class _ChangeMimeFilter(_MimeFilter):

	def _object( self, o ):
		return o.object

class _UGDStreamView(_UGDView):

	get_owned = users.User.getContainedStream
	get_shared = None
	_my_objects_may_be_empty = False
	_support_cross_user = False

	_MIME_FILTER_FACTORY = _ChangeMimeFilter

class _RecursiveUGDStreamView(_RecursiveUGDView):
	"""
	Accepts all the regular sorting and paging parameters (though note, you
	probably do not want to sort by anything other than the default, lastModified descending).

	Also accepts:

	batchBefore
		If given, this is the timestamp (floating point number in fractional
		unix seconds, as returned in ``Last Modified``) of the *youngest*
		change to consider returning. Thus, the most efficient way to page through
		this object is to *not* use ``batchStart``, but instead to set ``batchBefore``
		to the timestamp of the *oldest* change in the previous batch (always leaving
		``batchBefore`` at zero). Effectively, this defaults to the current time.
		(Note: the next/previous link relations do not currently take this into account.)

	"""
	_support_cross_user = False
	_my_objects_may_be_empty = False
	# It is an optimization to only look in the stream containers.
	# But if we have to fallback from the stream and look directly in the
	# shared containers, it is sadly incorrect
	_iter_ntiids_stream_only = False

	get_owned = users.User.getContainedStream
	get_shared = None

	# Default to paging us
	_DEFAULT_BATCH_SIZE = 100
	_DEFAULT_BATCH_START = 0
	_MIME_FILTER_FACTORY = _ChangeMimeFilter

	_needs_filtered = False # We do our own filtering as we page

	def getObjectsForId( self, user, ntiid ):
		containers = self._get_containerids_for_id( user, ntiid )
		self.context_cache.make_accumulator()
		batch_size, batch_start = self._get_batch_size_start()
		items_needed = self._DEFAULT_BATCH_SIZE
		if batch_size is not None and batch_start is not None:
			items_needed = batch_start + batch_size + 2

		before = float(self.request.params.get( 'batchBefore', -1 ))
		predicate = self._make_complete_predicate()
		for container in containers:
			self.get_owned( user, container,
							context_cache=self.context_cache,
							maxCount=items_needed,
							before=before,
							predicate=predicate)

		items = [self.context_cache.to_result(), (), ()] # owned, shared, public, for compatibility

		if not items[0] and not self._my_objects_may_be_empty \
		  and not (self._get_exclude_types() or self._get_accept_types()): # for bwc, if we filtered everything out, it's not a 404
			raise hexc.HTTPNotFound()
		return items



class _UGDAndRecursiveStreamView(_UGDView):
	"""
	Returns both the generated data and the stream data.

	.. warning :: This does not support paging/filtering or cross-user queries.
	"""

	_support_cross_user = False
	def __init__(self, request ):
		super(_UGDAndRecursiveStreamView,self).__init__( request )

	def __call__( self ):
		"""
		Overrides the normal mechanism to separate out the page
		data and the change data in separate keys.
		"""
		# FIXME: This doesn't support paging or filtering or cross-user security
		user, ntiid = self.user, self.ntiid
		self.check_cross_user()

		page_data, stream_data = self._getAllObjects( user, ntiid )
		all_data = []
		all_data += page_data
		all_data += stream_data
		# The legacy code expects { 'LastMod': 0, 'Items': [] }
		top_level = lists_and_dicts_to_ext_collection( all_data )

		# To that we add something more similar to our new collection
		# structure, buried under the 'Collection' key.
		# the end result is:
		# { 'LM': 0, 'Items': [], 'Collection': { 'Items': [ {stream} {page} ] } }

		collection = {}
		page_data = lists_and_dicts_to_ext_collection( page_data )
		page_data['Title'] = 'UGD'
		stream_data = lists_and_dicts_to_ext_collection( stream_data )
		stream_data['Title'] = 'Stream'
		collection['Items'] = [page_data, stream_data]
		top_level['Collection'] = collection
		return top_level


	def _getAllObjects( self, user, ntiid ):
		pageGet = _UGDView( self.request )
		streamGet = _RecursiveUGDStreamView( self.request )
		streamGet.context_cache = pageGet.context_cache
		streamGet._my_objects_may_be_empty = True
		page_data = ()
		try:
			page_data = pageGet.getObjectsForId( user, ntiid )
		except hexc.HTTPNotFound:
			# If the root object container DNE,
			# then we must have a stream, otherwise
			# the whole thing should 404
			streamGet._my_objects_may_be_empty = False

		stream_data = streamGet.getObjectsForId( user, ntiid )
		return page_data, stream_data

	def getObjectsForId( self, user, ntiid ):
		page_data, stream_data = self._getAllObjects( user, ntiid )
		all_data = []
		all_data += page_data
		all_data += stream_data
		return all_data

#: The link relationship type that can be used
#: to get all the visible replies to a Note
REL_REPLIES = 'replies'

from .pyramid_renderers import _md5_etag

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.INote)
class ReferenceListBasedDecorator(_util.AbstractTwoStateViewLinkDecorator):
	"""
	Decorates the external object based on the presence of things that
	reference it.

	In particular, this means adding the ``@@replies`` link if there are replies to fetch.
	It also means including the ``ReferencedByCount`` value if it exists,
	and calculating the ``RecursiveLikeCount``, if possible.

	The replies link accepts the same parameters as the UGD views (see
	:meth:`_UGDView._sort_filter_batch_result`); most useful are the batching and sorting
	parameters.
	"""
	false_view = REL_REPLIES
	true_view = REL_REPLIES
	predicate = staticmethod(lambda context, current_user: True)

	def decorateExternalMapping( self, context, mapping ):
		# Also add the reply count, if we have that information available

		extra_elements = ()
		reply_count = _reference_list_length( context )
		if reply_count >= 0:
			mapping['ReferencedByCount'] = reply_count

		mapping['RecursiveLikeCount'] = _reference_list_recursive_like_count( context )
		# Use the reply count and the maximum modification date
		# of the child as a "ETag" value to allow caching of the @@replies indefinitely
		max_last_modified = _reference_list_recursive_max_last_modified( context )
		etag = _md5_etag( reply_count, max_last_modified ).replace( '/', '_' )
		extra_elements = (etag,)

		super(RepliesLinkDecorator,self).decorateExternalMapping( context, mapping, extra_elements=extra_elements )


RepliesLinkDecorator = ReferenceListBasedDecorator # BWC
from .interfaces import IETagCachedUGDExternalCollection
from nti.dataserver.datastructures import LastModifiedCopyingUserList
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.INote,
			  permission=nauth.ACT_READ,
			  request_method='GET',
			  name=REL_REPLIES)
def replies_view(request):
	"""
	Given a threaded object, return all the objects in the same container
	that reference it.

	The ``subpath`` (part of the path after the view name) is ignored and can
	thus be used as a unique token for caching. (If it is present we do allow
	caching; see :class:`ReferenceListBasedDecorator` for its computation.)
	"""

	# First collect the objects
	the_user = users.User.get_user( psec.authenticated_userid( request ) )
	root_note = request.context

	result_iface = IUGDExternalCollection
	if request.subpath:
		#result_iface = IETagCachedUGDExternalCollection
		# temporarily disabled, see forums/views
		pass


	referents = LastModifiedCopyingUserList()
	referents.updateLastMod( root_note.lastModified )
	for child in root_note.referents:
		referents.append( child )
		referents.updateLastModIfGreater( child.lastModified )

	objs = (referents,)


	# Not all the params make sense, but batching does
	view = _UGDView( request, the_user, root_note.containerId )
	view._force_apply_security = True
	view.result_iface = result_iface
	view.ignore_broken = True
	return view._sort_filter_batch_objects( objs )
