#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for querying user generated data.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import weakref
import numbers

from zope import interface
from zope import component
from zope.proxy import ProxyBase

from pyramid.view import view_config
from pyramid import security as psec
from pyramid.threadlocal import get_current_request

from nti.appserver import httpexceptions as hexc
from nti.appserver import _util

from nti.contentlibrary import interfaces as lib_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.oids import to_external_oid

from nti.ntiids import ntiids

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.dataserver import liking
from nti.dataserver import authorization as nauth

from z3c.batching.batch import Batch

def lists_and_dicts_to_ext_collection( items ):
	""" Given items that may be dictionaries or lists, combines them
	and externalizes them for return to the user as a dictionary. If the individual items
	are ModDateTracking (have a lastModified value) then the returned
	dict will have the maximum value as 'Last Modified' """
	result = []
	# To avoid returning duplicates, we keep track of object
	# ids and only add one copy.
	oids = set()
	items = [item for item in items if item is not None]
	lastMod = 0
	for item in items:
		lastMod = max( lastMod, getattr( item, 'lastModified', 0) )
		if hasattr( item, 'itervalues' ):
			# ModDateTrackingOOBTrees tend to lose the custom
			# 'lastModified' attribute during persistence
			# so if there is a 'Last Modified' entry, go
			# for that
			if hasattr( item, 'get' ):
				lastMod = max( lastMod, item.get( 'Last Modified', 0 ) )
			item = item.itervalues()
		# None would come in because of weak refs, numbers
		# would come in because of Last Modified.
		# In the case of shared data, the object might
		# update but our container wouldn't
		# know it, so check for internal update times too
		for x in item:
			if x is None or isinstance( x, numbers.Number ):
				continue

			lastMod = max( lastMod, getattr( x, 'lastModified', 0) )
			add = True
			oid = to_external_oid( x, str( id(x) ) )

			if oid not in oids:
				oids.add( oid )
			else:
				add = False
			if add: result.append( x )

	result = LocatedExternalDict( { 'Last Modified': lastMod, 'Items': result } )
	return result

_REF_ATTRIBUTE = 'referenced_by' # TODO: Be absolutely sure this doesn't cause rewriting of the note in the DB

class RefProxy(ProxyBase):

	def __init__( self, obj ):
		super(RefProxy,self).__init__( obj )
		self._v_referenced_by = None

	def _referenced_by(self):
		return self._v_referenced_by
	def _set_referenced_by( self, nv ):
		self._v_referenced_by = nv
	referenced_by = property(_referenced_by, _set_referenced_by)

def _build_reference_lists( request, result_list ):
	proxies = {}
	setattr( request, '_build_reference_lists_proxies', proxies )
	def _referenced_by( x ):
		x = proxies[x]
		result = x.referenced_by
		if result is None:
			result = []
			x.referenced_by = result
		return result

	for i, item in enumerate(result_list):
		# Ensure every item gets the list if it could have replies
		if hasattr( item, 'inReplyTo' ):
			proxy = RefProxy( item )
			result_list[i] = proxy
			proxies[item] = proxy

	for item in result_list:
		inReplyTo = getattr( item, 'inReplyTo', None )

		if inReplyTo is not None:
			# This function blows up if the reply is from a different container.
			# and so didn't get proxied
			# That's not supposed to happen.
			# Also, we must maintain the proxy map ourself because the items we get
			# back from here are 'real' vs the things we just put in the result list
			_referenced_by( inReplyTo ).append( weakref.ref( item ) )
		for ref in getattr( item, 'references', () ):
			if ref is not None:
				_referenced_by( ref ).append( weakref.ref( item ) )

def _reference_list_length( x ):
	refs = getattr( x, _REF_ATTRIBUTE, _reference_list_length )
	if refs is not _reference_list_length:
		if refs is None:
			return 0
		return len(refs)
	return -1 # distinguish no refs vs no data

SORT_KEYS = {
	'lastModified': lambda x: getattr( x, 'lastModified', 0 ), # TODO: Adapt to dublin core?
	'LikeCount': liking.like_count,
	'ReferencedByCount': ( _build_reference_lists, _reference_list_length )
	}
SORT_DIRECTION_DEFAULT = {
	'LikeCount': 'descending',
	'ReferencedByCount': 'descending',
	'lastModified': 'descending'
	}
FILTER_NAMES = {
	'TopLevel': lambda x: getattr( x, 'inReplyTo', None ) is None
	# This won't work for the Change objects. (Try Acquisition?) Do we need it for them?
	}

class _UGDView(object):
	"""
	The base view for user generated data.
	"""

	get_owned = users.User.getContainer
	get_shared = users.User.getSharedContainer
	get_public = None

	def __init__(self, request ):
		self.request = request
		self._my_objects_may_be_empty = True

	def __call__( self ):
		user, ntiid = self.request.context.user, self.request.context.ntiid
		result = lists_and_dicts_to_ext_collection( self.getObjectsForId( user, ntiid ) )
		self._sort_filter_batch_result( result )
		result.__parent__ = self.request.context
		result.__name__ = ntiid
		return result

	def getObjectsForId( self, user, ntiid ):
		"""
		Returns a sequence of values that can be passed to
		:func:`lists_and_dicts_to_ext_collection`.

		:raises nti.appserver.httpexceptions.HTTPNotFound: If no actual objects can be found.
		"""
		__traceback_info__ = user, ntiid
		mystuffDict = self.get_owned( user, ntiid ) if self.get_owned else ()
		sharedstuffList = self.get_shared( user, ntiid) if self.get_shared else ()
		publicDict = self.get_public( user, ntiid ) if self.get_public else ()
		# To determine the existence of the container,
		# My stuff either exists or it doesn't. The others, being shared,
		# may be empty or not empty.
		if (mystuffDict is None \
			or (not self._my_objects_may_be_empty and not mystuffDict)) \
			   and not sharedstuffList \
			   and not publicDict:
			raise hexc.HTTPNotFound(ntiid)

		return (mystuffDict, sharedstuffList, publicDict)

	def _sort_filter_batch_result( self, result ):
		"""
		Sort, filter, and batch (page) the result by modifying it in place. This method
		sorts by lastModified by default, but everything else comes from the query parameters:

		sortOn
			The field to sort on. Options are ``lastModified``, ``LikeCount`` and ``ReferencedByCount``.
			Only ``lastModified`` is valid for the stream views.

		sortOrder
			The sort direction. Options are ``ascending`` and ``descending``.

		filter
			Whether to filter the returned data in some fashion. Only ``TopLevel`` is defined, and
			only for the data views (not the stream). It causes only objects that are not
			replies to something else to be returned.

		batchSize
			Integer giving the page size. Must be greater than zero. Paging only happens when
			this is supplied together with ``batchStart``

		batchStart
			Integer giving the index of the first object to return, starting with zero. Paging only
			happens when this is supplied together with ``batchSize``.

		:param dict result: The result dictionary that will be returned to the client.
			Contains the ``Items`` list of all items found. You may add keys to the dictionary.
			You may (and should) modify the Items list directly.
		"""

		# Before we filter and batch, we sort. Some filter operations need the sorted
		# data
		result_list = result['Items']
		result['TotalItemCount'] = len(result_list)
		# The request keys match what z3c.table does
		sort_on = self.request.params.get( 'sortOn', 'lastModified' )
		sort_order = self.request.params.get( 'sortOrder', SORT_DIRECTION_DEFAULT.get( sort_on, 'ascending' ) )
		sort_key_function = SORT_KEYS.get( sort_on, SORT_KEYS['lastModified'] )
		if isinstance( sort_key_function, tuple ):
			prep_function = sort_key_function[0]
			sort_key_function = sort_key_function[1]
			prep_function( self.request, result_list )

		result_list.sort( key=sort_key_function,
						  reverse=(sort_order == 'descending') )

		# TODO: Which is faster and more efficient? The built-in filter function which allocates
		# a new list but iterates fast, or iterating in python and removing from the existing list?
		# Since the list is really an array, removing from it is actually slow
		filter_name = self.request.params.get( 'filter' )
		if filter_name in FILTER_NAMES:
			# Be nice and make sure the reply count gets included if
			# it isn't already and we're after just the top level.
			# Must do this before filtering
			if filter_name == 'TopLevel' and sort_key_function is not _reference_list_length:
				_build_reference_lists( self.request, result_list )
			result_list = filter(FILTER_NAMES[filter_name], result_list)
			result['Items'] = result_list

		batch_size = self.request.params.get( 'batchSize' )
		batch_start = self.request.params.get( 'batchStart' )
		if batch_size and batch_start:
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
				# TODO: With a slight change to the renderer, we could directly
				# externalize by iterating this and avoid creating the sublist
				result_list = list(Batch( result_list, batch_start, batch_size ))

			result['Items'] = result_list
			# TODO: Inserting links to next/previous/start/end

class _RecursiveUGDView(_UGDView):

	def __init__(self,request):
		super(_RecursiveUGDView,self).__init__(request)

	def getObjectsForId( self, user, ntiid ):
		containers = ()

		if ntiid == ntiids.ROOT:
			containers = set(user.iterntiids())
		else:
			library = self.request.registry.getUtility( lib_interfaces.IContentPackageLibrary )
			tocEntries = library.childrenOfNTIID( ntiid )

			containers = {toc.ntiid for toc in tocEntries} # children
			containers.add( ntiid ) # item

		# We always include the unnamed root (which holds things like CIRCLED)
		# NOTE: This is only in the stream. Normally we cannot store contained
		# objects with an empty container key, so this takes internal magic
		containers.add( '' ) # root

		items = []
		for container in containers:
			try:
				items += super(_RecursiveUGDView,self).getObjectsForId( user, container )
			except hexc.HTTPNotFound:
				pass

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
				li = len(i)
				if li >= 2 or (li == 1 and 'Last Modified' not in i):
					empty = False
					break

		if empty:
			# Let this throw if it did before
			super(_RecursiveUGDView,self).getObjectsForId( user, ntiid )

		return items

class _UGDStreamView(_UGDView):

	def __init__(self, request ):
		super(_UGDStreamView,self).__init__(request)
		self.get_owned = users.User.getContainedStream
		self.get_shared = None
		self._my_objects_may_be_empty = False

class _RecursiveUGDStreamView(_RecursiveUGDView):

	def __init__(self,request):
		super(_RecursiveUGDStreamView,self).__init__(request)
		self.get_owned = users.User.getContainedStream
		self.get_shared = None
		self._my_objects_may_be_empty = False

class _UGDAndRecursiveStreamView(_UGDView):

	def __init__(self, request ):
		super(_UGDAndRecursiveStreamView,self).__init__( request )

	def __call__( self ):
		"""
		Overrides the normal mechanism to separate out the page
		data and the change data in separate keys.
		"""
		user, ntiid = self.request.context.user, self.request.context.ntiid
		page_data, stream_data = self._getAllObjects( user, ntiid )
		all_data = []; all_data += page_data; all_data += stream_data
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

REL_REPLIES = 'replies'



@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.INote)
class RepliesLinkDecorator(_util.AbstractTwoStateViewLinkDecorator):
	"""
	Adds the link to get replies.
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
	view = _UGDView( request )
	view._my_objects_may_be_empty = True
	objs = view.getObjectsForId( users.User.get_user( psec.authenticated_userid( request ) ),
								 request.context.containerId )
	result = lists_and_dicts_to_ext_collection( objs )

	def test(x):
		return request.context in getattr( x, 'references', () ) or request.context == getattr( x, 'inReplyTo', None )
	result_list = filter( test,
						  result['Items'] )
	result['Items'] = result_list
	return result
