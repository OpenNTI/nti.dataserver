#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import shutil
import datetime
import operator
import tempfile
from collections import Mapping

from ZODB.utils import u64

import simplejson

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.forums import VIEW_CONTENTS

from nti.app.renderers.interfaces import IETagCachedUGDExternalCollection
from nti.app.renderers.interfaces import IPreRenderResponseCacheController
from nti.app.renderers.interfaces import ILongerCachedUGDExternalCollection
from nti.app.renderers.interfaces import IUseTheRequestContextUGDExternalCollection

from nti.appserver.dataserver_pyramid_views import GenericGetView

from nti.appserver.pyramid_authorization import is_readable

from nti.appserver.traversal import find_interface

from nti.appserver.ugd_query_views import Operator
from nti.appserver.ugd_feed_views import AbstractFeedView
from nti.appserver.ugd_query_views import _combine_predicate
from nti.appserver.ugd_query_views import _UGDView as UGDQueryView

from nti.cabinet.filer import transfer_to_native_file

from nti.common.random import generate_random_hex_string

from nti.coremetadata.interfaces import IModeledContentBody

from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import IACLProvider

from nti.dataserver import authorization as nauth

from nti.externalization.externalization import to_external_object

from nti.namedfile.interfaces import INamedFile

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

_view_defaults = dict(route_name='objects.generic.traversal',
					  renderer='rest')
_c_view_defaults = _view_defaults.copy()
_c_view_defaults.update(permission=nauth.ACT_CREATE,
						request_method='POST')
_r_view_defaults = _view_defaults.copy()
_r_view_defaults.update(permission=nauth.ACT_READ,
						request_method='GET')
_d_view_defaults = _view_defaults.copy()
_d_view_defaults.update(permission=nauth.ACT_DELETE,
						request_method='DELETE')

@view_config(context=frm_interfaces.IHeadlineTopic)
@view_config(context=frm_interfaces.IForum)
@view_config(context=frm_interfaces.IGeneralForum)
@view_config(context=frm_interfaces.IGeneralBoard)
@view_config(context=frm_interfaces.IPersonalBlog)  # need to re-list this one
@view_config(context=frm_interfaces.IPersonalBlogEntry)  # need to re-list this one
@view_config(context=frm_interfaces.IPersonalBlogComment)  # need to re-list this one
@view_config(context=frm_interfaces.IPersonalBlogEntryPost)  # need to re-list this one
@view_config(context=frm_interfaces.IGeneralHeadlineTopic)  # need to re-list
@view_config(context=frm_interfaces.IGeneralHeadlinePost)  # need to re-list
@view_config(context=frm_interfaces.IGeneralForumComment)  # need to re-list
@view_config(context=frm_interfaces.IPost)
@view_defaults(**_r_view_defaults)
class ForumGetView(GenericGetView):
	""" 
	Support for simply returning the blog item 
	"""
	def __call__(self):
		result = super(ForumGetView, self).__call__()
		if result is not None:
			pass
			# current = result
			# readable = True
			# XXX FIXME: WTF are we doing here?
			# This is completely bypassing the ACL model
			# which *ALREADY* takes the parents into account.
			# JAM: Commenting out, this breaks any generalization.
			# while readable and current is not None and not IEntity.providedBy(current):
			# 	readable = is_readable(current)
			# 	current = getattr(current, '__parent__', None)
			# if not readable:
			# 	raise hexc.HTTPForbidden()
		return result

@view_config(context=frm_interfaces.IBoard)
@view_config(context=frm_interfaces.IGeneralHeadlineTopic)
@view_config(context=frm_interfaces.IPersonalBlogEntry)
@view_defaults(name=VIEW_CONTENTS, **_r_view_defaults)
class ForumsContainerContentsGetView(UGDQueryView):
	"""
	The ``/contents`` view for the forum objects we are using.

	The contents fully support the same sorting and paging parameters
	as the UGD views.
	"""

	def __init__(self, request):
		self.request = request
		super(ForumsContainerContentsGetView, self).__init__(request,
															 the_user=self,
															 the_ntiid=self.request.context.__name__)

		# The user/community is really the 'owner' of the data
		self.user = find_interface(self.request.context, IEntity)

		if frm_interfaces.IBoard.providedBy(self.request.context):
			self.result_iface = ILongerCachedUGDExternalCollection

		# If we were invoked with a subpath, then it must be the tokenized
		# version so we can allow for good caching, as we will change the token
		# when the data changes.
		# XXX Except the browser application sometimes does and sometimes does
		# not make a fresh request for the /contents. It seems to be based on
		# where you're coming from. It's even possible for it to get in the state
		# that the order of your page views shows two different sets of contents
		# for the same forum.
		# XXX I think part of this may be because some parent containers (Forum) do not
		# get modification times updated on them when grandchildren change. In the
		# immediate term, we do this just with the topics, where we know one level
		# works.
		# XXX It seems that the "parent" objects can be cached at the application level, meaning
		# that the application never sees the updated contents URLs, making it impossible
		# to HTTP cache them.
		if False and frm_interfaces.IHeadlineTopic.providedBy(request.context) and self.request.subpath:
			self.result_iface = IETagCachedUGDExternalCollection

	def __call__(self):
		try:
			# See if we are something that maintains reliable modification dates
			# including our children.
			# (only ITopic is registered for this). If so, then we want to use
			# this fact when we create the ultimate return ETag.
			# We also want to bail now with 304 Not Modified if we can
			controller = IPreRenderResponseCacheController(self.request.context)
			controller(self.request.context, {'request': self.request})
			self.result_iface = IUseTheRequestContextUGDExternalCollection
		except TypeError:
			pass
		return super(ForumsContainerContentsGetView, self).__call__()

	def _is_readable(self, x):
		result = True
		if IACLProvider.providedBy(x) or frm_interfaces.IACLEnabled.providedBy(x):
			result = is_readable(x, self.request)
		return result

	def _make_complete_predicate(self, operator=Operator.intersection):
		predicate = super(ForumsContainerContentsGetView, self)._make_complete_predicate(operator)
		predicate = _combine_predicate(self._is_readable, predicate, Operator.intersection)
		return predicate

	def getObjectsForId(self, *args):
		return (self.request.context,)

@view_config(context=frm_interfaces.IDefaultForumBoard)
@view_defaults(name=VIEW_CONTENTS,
				**_r_view_defaults)
class DefaultForumBoardContentsGetView(ForumsContainerContentsGetView):

	def __init__(self, request):
		# Make sure that if it's going to have a default, it does
		try:
			request.context.createDefaultForum()
		except (TypeError, AttributeError):
			pass
		super(DefaultForumBoardContentsGetView, self).__init__(request)

	def _update_last_modified_after_sort(self, objects, result):
		# We need to somehow take the modification date of the children
		# into account since we aren't tracking that directly (it doesn't
		# propagate upward). TODO: This should be cached somewhere
		board = objects[0]
		forumLastMod = max((x.lastModified for x in board.itervalues() if is_readable(x, self.request)))
		lastMod = max(result.lastModified, forumLastMod)
		result.lastModified = lastMod
		super(DefaultForumBoardContentsGetView, self)._update_last_modified_after_sort(objects, result)

@view_config(context=frm_interfaces.IForum)
@view_config(context=frm_interfaces.IGeneralForum)
@view_config(context=frm_interfaces.IPersonalBlog)
@view_defaults(name=VIEW_CONTENTS, **_r_view_defaults)
class ForumContentsGetView(ForumsContainerContentsGetView):
	"""
	Adds support for sorting by ``NewestDescendantCreatedTime`` of the
	individual topics, and makes sure that the Last Modified time
	reflects that value.

	Parameters:

	sortOn
		Adds ``NewestDescendantCreatedTime`` and ``PostCount``. Both
		of these break ties based on the time the object was created.

	searchTerm
		An extremely expensive way to search because it requires
		fetching all the objects from the database. Why not just
		do a real search?
	"""

	SORT_KEYS = ForumsContainerContentsGetView.SORT_KEYS.copy()
	SORT_KEYS['PostCount'] = operator.attrgetter('PostCount', 'createdTime')
	SORT_KEYS['NewestDescendantCreatedTime'] = operator.attrgetter('NewestDescendantCreatedTime', 'createdTime')

	def _make_heapq_NewestDescendantCreatedTime_descending_key(self, plain_key):
		def _negate_tuples(x):
			tpl = plain_key(x)
			return (-tpl[0], -tpl[1])
		return _negate_tuples
	_make_heapq_PostCount_descending_key = _make_heapq_NewestDescendantCreatedTime_descending_key

	def __call__(self):
		result = super(ForumContentsGetView, self).__call__()

		if self.request.context:
			# Sigh. Loading all the objects.
			# TODO: We are doing this even for comments during the RSS/Atom feed process, which
			# is weird.
			# NOTE: Using the key= argument fails because it masks AttributeErrors and results in
			# heterogenous comparisons
			newest_time = max(getattr(x, 'NewestDescendantCreatedTime', 0) 
							  for x in self.request.context.values())
			newest_time = max(result.lastModified, newest_time)
			result.lastModified = newest_time
			result['Last Modified'] = newest_time
		return result

@view_config(context=frm_interfaces.IHeadlineTopic,
			 name='feed.atom')
@view_config(context=frm_interfaces.IHeadlineTopic,
			 name='feed.rss')
@view_config(context=frm_interfaces.IForum,
			 name='feed.atom')
@view_config(context=frm_interfaces.IForum,
			 name='feed.rss')
@view_defaults(http_cache=datetime.timedelta(hours=1), **_r_view_defaults)
class ForumContentsFeedView(AbstractFeedView):
	_data_callable_factory = ForumContentsGetView

	def _feed_title(self):
		return self.request.context.title

	def _object_and_creator(self, ipost_or_itopic):
		title = ipost_or_itopic.title
		# The object to render is either the 'story' (blog text) or the post itself
		if frm_interfaces.IHeadlineTopic.providedBy(ipost_or_itopic):
			data_object = ipost_or_itopic.headline
		else:
			data_object = ipost_or_itopic
		return data_object, ipost_or_itopic.creator, title, ipost_or_itopic.tags

_e_view_defaults = _r_view_defaults.copy()
_e_view_defaults.update(permission=nauth.ACT_NTI_ADMIN,
						name='export')

@view_config(context=frm_interfaces.IBoard)
@view_config(context=frm_interfaces.IForum)
@view_config(context=frm_interfaces.ITopic)
@view_config(context=frm_interfaces.IPost)
@view_defaults(**_e_view_defaults)
class ExportObjectView(GenericGetView):

	def _ext_filename(self, context):
		name = context.filename or context.name
		try:
			oid = context._p_oid
			_, ext = os.path.splitext(name)
			name = str(u64(oid)) + ext
		except AttributeError:
			pass
		return name

	def _process_files(self, context, out_dir):
		if isinstance(context, Mapping):
			for value in context.values():
				self._process_files(value, out_dir)
		elif IModeledContentBody.providedBy(context):
			for value in context.body or ():
				if INamedFile.providedBy(value):
					name = self._ext_filename(value)
					name = os.path.join(out_dir, name)
					transfer_to_native_file(value, name)

	def __call__(self):
		result = to_external_object(self.context, name='exporter', decorate=False)
		try:
			out_dir = tempfile.mkdtemp()
			with open(os.path.join(out_dir, 'data.json'), "wb") as fp:
				simplejson.dump(result, fp, indent='\t', sort_keys=True)
			self._process_files(self.context, out_dir)
			
			base_name = tempfile.mktemp() + "_" + generate_random_hex_string(6)
			result = shutil.make_archive(base_name, 'zip', out_dir)
		
			response = self.request.response
			response.content_encoding = str('identity')
			response.content_type = str('application/x-gzip; charset=UTF-8')
			response.content_disposition = str('attachment; filename="export.zip"')
			response.body_file = open(result, "rb")
			return response
		finally:
			shutil.rmtree(out_dir)
	
del _view_defaults
del _c_view_defaults
del _d_view_defaults
del _e_view_defaults
del _r_view_defaults
