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
import weakref
import numbers
import functools

from zope import interface
from zope import component
from zope.proxy import ProxyBase

from pyramid.view import view_config
from pyramid import security as psec
from pyramid.threadlocal import get_current_request

from nti.appserver import httpexceptions as hexc
from nti.appserver import _util
from nti.appserver import _view_utils
from nti.appserver._view_utils import get_remote_user
from nti.appserver.pyramid_authorization import is_readable

from nti.contentlibrary import interfaces as lib_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.oids import to_external_oid

from nti.externalization.externalization import to_standard_external_last_modified_time
from nti.externalization.externalization import to_standard_external_created_time

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

from nti.utils.property import alias

from z3c.batching.batch import Batch

from perfmetrics import metricmethod

def lists_and_dicts_to_ext_collection( lists_and_dicts, predicate=id ):
	""" Given items that may be dictionaries or lists, combines them
	and externalizes them for return to the user as a dictionary. If the individual items
	are ModDateTracking (have a lastModified value) then the returned
	dict will have the maximum value as 'Last Modified'

	:param callable predicate: Objects will only make it into the final 'Items' list
		if this function returns true for all of them. Defaults to a True filter.
	"""
	result = []
	# To avoid returning duplicates, we keep track of object
	# ids and only add one copy.
	oids = set()
	lists_and_dicts = [item for item in lists_and_dicts if item is not None]
	lastMod = 0
	for list_or_dict in lists_and_dicts:
		lastMod = max( lastMod, getattr( list_or_dict, 'lastModified', 0) )
		if hasattr( list_or_dict, 'itervalues' ):
			# ModDateTrackingOOBTrees tend to lose the custom
			# 'lastModified' attribute during persistence
			# so if there is a 'Last Modified' entry, go
			# for that
			if hasattr( list_or_dict, 'get' ):
				lastMod = max( lastMod, list_or_dict.get( 'Last Modified', 0 ) )
			to_iter = list_or_dict.itervalues()
		else:
			# then it must be a 'list'
			to_iter = list_or_dict
		# None would come in because of weak refs, numbers
		# would come in because of Last Modified.
		# In the case of shared data, the object might
		# update but our container wouldn't
		# know it, so check for internal update times too
		for x in to_iter:
			if x is None or isinstance( x, numbers.Number ) or not predicate(x):
				continue

			lastMod = max( lastMod, getattr( x, 'lastModified', 0) )
			add = True
			oid = to_external_oid( x, str( id(x) ) )

			if oid not in oids:
				oids.add( oid )
			else:
				add = False
			if add:
				result.append( x )

	result = LocatedExternalDict( { 'Last Modified': lastMod, 'Items': result } )
	result.mimeType = nti_mimetype_with_class( None )
	return result

_REF_ATTRIBUTE = 'referenced_by'

class RefProxy(ProxyBase):
	# Unless we have slots, we set properties of the underlying object, which is bad,
	# it has cross-thread implications and defeats the point of a proxy in the first place
	__slots__ = ('_v_referenced_by', '__weakref__')
	def __init__( self, obj ):
		super(RefProxy,self).__init__( obj )
		self._v_referenced_by = None
		self._v_recursive_like_count = None

	referenced_by = alias( '_v_referenced_by' )

def _build_reference_lists( request, result_list ):
	if hasattr( request, '_build_reference_lists_proxies' ):
		return

	proxies = {}
	setattr( request, '_build_reference_lists_proxies', proxies )
	fake_proxies = {} # so we only log once
	def _referenced_by( reference_to, reference_from=None ):
		try:
			orig = reference_to
			reference_to = proxies.get( reference_to, None )
			if reference_to is None:
				reference_to = orig
				reference_to = fake_proxies[reference_to]
		except KeyError:
			# So this means that we found something in the reference chain that was not
			# in the collection itself. Assuming we're looking at shared data in addition to owned data,
			# and knowing that ThreadableMixin is implemented with weakrefs, this means one of a few things:
			# First, there's cross-container referencing going on. The containerIDs won't match. That's not
			# supposed to be allowed. We haven't actually seen that yet.
			# Second, the note has been deleted but the weak ref hasn't cleaned up yet.
			# Third, the item was shared with this user at one point and no longer is.

			# In the later two cases, we will report on ID that the client won't be able to find and put into the thread,
			# so it will appear to be 'deleted'
			level = logging.DEBUG
			if hasattr( reference_to, 'inReplyTo' ) and not getattr( reference_to, 'inReplyTo' ):
				level = logging.WARN # If it was a root object, this is bad. The entire thread could be hidden
			logger.log( level, "Failed to get proxy for %s/%s/%s. Illegal reference chain from %s/%s?",
						  reference_to, getattr( reference_to, 'containerId', None ), id(reference_to),
						  reference_from, getattr( reference_from, 'containerId', None ))
			proxy = fake_proxies[reference_to] = RefProxy( reference_to )
			result = proxy.referenced_by = []
			return result # return a temp list that's not persistent
		result = reference_to.referenced_by
		if result is None:
			result = reference_to.referenced_by = []

		return result

	for i, item in enumerate(result_list):
		# Ensure every item gets the list if it could have replies
		if hasattr( item, 'inReplyTo' ):
			proxy = RefProxy( item )
			result_list[i] = proxy
			proxies[item] = proxy

	for item in result_list:
		inReplyTo = getattr( item, 'inReplyTo', None )
		__traceback_info__ = item, inReplyTo, getattr( item, 'containerId', None )

		if inReplyTo is not None:
			# Also, we must maintain the proxy map ourself because the items we get
			# back from here are 'real' vs the things we just put in the result list
			_referenced_by( inReplyTo, item ).append( weakref.ref( item ) )
		for ref in getattr( item, 'references', () ):
			if ref is not None and ref is not inReplyTo:
				_referenced_by( ref, item ).append( weakref.ref( item ) )

def _reference_list_length( x ):
	refs = getattr( x, _REF_ATTRIBUTE, _reference_list_length )
	if refs is not _reference_list_length:
		if refs is None:
			return 0
		return len(refs)
	return -1 # distinguish no refs vs no data

def _reference_list_objects( x ):
	refs = getattr( x, _REF_ATTRIBUTE, _reference_list_objects )
	if refs is not _reference_list_objects and refs is not None:
		return (x() for x in refs)
	else:
		return ()

def _reference_list_recursive_like_count( proxy ):
	# There is probably not much use in caching this? It's just a simple sum
	# across a list and everything should be in memory after the first time?
	return sum( (liking_like_count( x ) for x in _reference_list_objects( proxy ) ),
				liking_like_count( proxy ))


def _combine_predicate( new, old ):
	if not old:
		return new
	return lambda obj: new(obj) and old(obj)

def _meonly_predicate_factory( request ):
	"""
	Creates a filter that will return things that only belong to (were created by)
	the current user.

	Note that this is a manual filtering and requires loading all the
	data into memory; it can be implemented more efficiently (avoiding
	loading all the data) by adjusting
	:meth:`_UGDView.getObjectsForId` to simply *not* load the shared
	data when the filter is ``MeOnly``. However, profiling (Jan 2013)
	shows that most of the overhead is actually in externalization and
	loading and filtering the objects is relatively fast---the
	difference amounts to less than 15%; this depends, however, on the
	effectiveness of the storage cache and the amount of objects being
	filtered out. Doing it manually lets us get accurate values for
	ReferencedByCount and RecursiveLikeCount.

	The meaning of "me" defaults to the user who created the data (request.context.user
	or request.context, if it is a IUser).

	"""
	me = request.context.user if not nti_interfaces.IUser.providedBy( request.context ) else request.context # TODO: Can probably use lineage for this.
	me_uname = me.username
	def _filter(o):
		try:
			return getattr( o.creator, 'username', o.creator ) == me_uname
		except AttributeError:
			return False
	return _filter

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
	'ReferencedByCount': ( _build_reference_lists, _reference_list_length ),
	'RecursiveLikeCount': (_build_reference_lists, _reference_list_recursive_like_count)
	}
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
	'MeOnly': (_meonly_predicate_factory,),
	}

class _MimeFilter(object):

	def __init__( self, accept_types ):
		self.accept_types = accept_types

	def _mimetype_from_object( self, o ):
		return nti_mimetype_from_object( o )

	def __call__( self, o ):
		return self._mimetype_from_object(o) in self.accept_types

class _UGDView(_view_utils.AbstractAuthenticatedView):
	"""
	The base view for user generated data.
	"""

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
			if self.user != self.getRemoteUser():
				raise hexc.HTTPForbidden()

	def __call__( self ):
		self.check_cross_user()

		user, ntiid = self.user, self.ntiid
		the_objects = self.getObjectsForId( user, ntiid )
		# Apply cross-user security if needed
		if user != self.getRemoteUser():
			predicate = is_readable
		else:
			predicate = id # always true
		result = lists_and_dicts_to_ext_collection( the_objects, predicate )
		self._sort_filter_batch_result( result )
		result.__parent__ = self.request.context
		result.__name__ = ntiid
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

	@metricmethod
	def getObjectsForId( self, user, ntiid ):
		"""
		Returns a sequence of values that can be passed to
		:func:`lists_and_dicts_to_ext_collection`.

		:raises nti.appserver.httpexceptions.HTTPNotFound: If no actual objects can be found.
		"""

		remote_user = self.getRemoteUser()
		get_shared = None
		if self._force_shared_objects or user == remote_user:
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

	@metricmethod
	def _sort_filter_batch_result( self, result ):
		"""
		Sort, filter, and batch (page) the result dictionary by
		modifying it in place, potentially adding new keys (this
		implementation adds several keys; see below). This method
		sorts by ``lastModified`` by default, but everything else
		comes from the following query parameters:

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
			``batchStart``

		batchStart
			Integer giving the index of the first object to return,
			starting with zero. Paging only happens when this is
			supplied together with ``batchSize``.

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

		# Before we filter and batch, we sort. Some filter operations need the sorted
		# data.
		### XXX Which ones? Unit tests don't break if we don't sort first, so for efficiency
		# we're not

		result_list = result['Items']
		result['TotalItemCount'] = result['FilteredTotalItemCount'] = len(result_list)

		# The request keys match what z3c.table does
		sort_on = self.request.params.get( 'sortOn', self._DEFAULT_SORT_ON )
		sort_order = self.request.params.get( 'sortOrder', self.SORT_DIRECTION_DEFAULT.get( sort_on, 'ascending' ) )
		sort_key_function = self.SORT_KEYS.get( sort_on, self.SORT_KEYS['lastModified'] )

		# TODO: Which is faster and more efficient? The built-in filter function which allocates
		# a new list but iterates fast, or iterating in python and removing from the existing list?
		# Since the list is really an array, removing from it is actually slow

		predicate = None # We build an uber predicate that handles all filtering in one pass through the list
		predicate = self._make_accept_predicate( )
		if predicate is None:
			# accept takes priority over exclude
			predicate = self._make_exclude_predicate()

		filter_names = self._get_filter_names()
		# Be nice and make sure the reference-based counts get included if we are going to be throwing
		# away all child data
		# Must do this before filtering (see also comments in _meonly_predicate_factory)
		if 'TopLevel' in filter_names:
			_build_reference_lists( self.request, result_list )

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

		if predicate:
			result_list = filter(predicate, result_list)
			result['FilteredTotalItemCount'] = len(result_list)
			result['Items'] = result_list

		# Finally, sort the smallest set.
		if isinstance( sort_key_function, tuple ):
			prep_function = sort_key_function[0]
			sort_key_function = sort_key_function[1]
			prep_function( self.request, result_list )

		# Stable sort, which may be important
		result_list.sort( key=sort_key_function,
						  reverse=(sort_order == 'descending') )


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

			if batch_start >= len(result_list):
				# Batch raises IndexError
				result_list = []
			else:
				result_list = Batch( result_list, batch_start, batch_size )
				# Insert links to the next and previous batch
				next_batch, prev_batch = result_list.next, result_list.previous
				for batch, rel in ((next_batch, 'batch-next'), (prev_batch, 'batch-prev')):
					if batch is not None and batch != result_list:
						batch_params = self.request.params.copy()
						batch_params['batchStart'] = batch.start
						link_next_href = self.request.current_route_path( _query=sorted(batch_params.items()) ) # sort for reliable testing
						link_next = Link( link_next_href, rel=rel )
						result.setdefault( 'Links', [] ).append( link_next )

			result['Items'] = result_list

		return result

class _RecursiveUGDView(_UGDView):
	"""
	Just like a normal :class:`._UGDView`, but recurses through all the NTIID
	containers beneath the given NTIID. The unnamed container is always included.
	If the :data:`.ntiids.ROOT` is given, then all NTIID containers of the user
	are examined (the hierarchy is effectively ignored).
	"""

	_iter_ntiids_stream_only=False
	_iter_ntiids_include_stream=True

	@metricmethod
	def getObjectsForId( self, user, ntiid ):
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

		exc_info = None
		items = []
		for container in containers:
			try:
				items.extend( super(_RecursiveUGDView,self).getObjectsForId( user, container ) )
			except hexc.HTTPNotFound:
				exc_info = sys.exc_info()

		# We are not found iff the root container DNE (empty is OK)
		# and the children are empty/DNE. In other words, if
		# accessing UGD for this container would throw,
		# so does accessing recursive.
		items = [x for x in items if x is not None] # TODO: Who gives us back a None? Seen on the Root with MeOnly filter
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

		return items

class _ChangeMimeFilter(_MimeFilter):

	def _mimetype_from_object( self, o ):
		return nti_mimetype_from_object( o.object ) if o.object else None

class _UGDStreamView(_UGDView):

	get_owned = users.User.getContainedStream
	get_shared = None
	_my_objects_may_be_empty = False
	_support_cross_user = False

	_MIME_FILTER_FACTORY = _ChangeMimeFilter

class _RecursiveUGDStreamView(_RecursiveUGDView):

	_support_cross_user = False
	_my_objects_may_be_empty = False
	# It is an optimization to only look in the stream containers.
	# But if we have to fallback from the stream and look directly in the
	# shared containers, it is sadly incorrect
	_iter_ntiids_stream_only = False

	get_owned = users.User.getContainedStream
	get_shared = None


	_DEFAULT_BATCH_SIZE = 100
	_DEFAULT_BATCH_START = 0
	_MIME_FILTER_FACTORY = _ChangeMimeFilter

	def _sort_filter_batch_result( self, result ):
		"""
		Excludes change objects that refer to a missing object or creator due to weak refs.
		"""

		# Do this before the filters and what not on the top level so that the item count
		# makes sense
		#_entity_cache = {}
		#def _entity_exists( uname ):
		#	if uname not in _entity_cache:
		#		_entity_cache[uname] = users.Entity.get_entity( username=uname ) is not None
		#	return _entity_cache[uname]
		# If for some reason weak refs aren't clearing when we expect them to, we can
		# include the above in this clause.

		result['Items'] = [x for x in result['Items'] if x and x.object is not None and x.creator]
		super(_RecursiveUGDStreamView,self)._sort_filter_batch_result( result )



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
		super(RepliesLinkDecorator,self).decorateExternalMapping( context, mapping )
		# Also add the reply count, if we have that information available
		request = get_current_request()
		if request:
			proxies = getattr( request, '_build_reference_lists_proxies', None )
			if proxies:
				proxy = proxies.get( context, context )
				reply_count = _reference_list_length( proxy )
				if reply_count >= 0:
					mapping['ReferencedByCount'] = reply_count

				mapping['RecursiveLikeCount'] = _reference_list_recursive_like_count( proxy )


RepliesLinkDecorator = ReferenceListBasedDecorator # BWC

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
	"""

	# First collect the objects

	the_user = users.User.get_user( psec.authenticated_userid( request ) )
	objs = _UGDView.do_getObjects( the_user, request.context.containerId, the_user,
								   allow_empty=True )

	result = lists_and_dicts_to_ext_collection( objs )

	def test(x):
		return request.context in getattr( x, 'references', () ) or request.context == getattr( x, 'inReplyTo', None )
	result_list = filter( test,
						  result['Items'] )
	result['Items'] = result_list

	# Not all the params make sense, but batching does
	return _UGDView( request, the_user, request.context.containerId )._sort_filter_batch_result( result )
