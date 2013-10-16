#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for relevant UGD

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from pyramid import httpexceptions as _hexc

from nti.appserver import httpexceptions as hexc
from nti.appserver import interfaces as app_interfaces
from nti.appserver import ugd_query_views as query_views

from nti.contentlibrary import interfaces as lib_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import LocatedExternalDict

from nti.dataserver.mimetype import nti_mimetype_with_class

union_operator = query_views.Operator.union
intersection_operator = query_views.Operator.intersection

class _RelevantUGDView(query_views._UGDView):
	
	lastModified = 0

	def _make_accept_predicate( self ):
		accept_types = ('application/vnd.nextthought.redaction',)
		return self._MIME_FILTER_FACTORY(accept_types)
		
	def _make_complete_predicate(self, operator=union_operator):
		# accepted mime_types
		predicate = self._make_accept_predicate()

		# top level objects
		top_level_filter = 'TopLevel'
		filter_names = (top_level_filter, 'OnlyMe')
		for filter_name in filter_names:
			the_filter = self.FILTER_NAMES[filter_name]
			if isinstance(the_filter, tuple):
				the_filter = the_filter[0](self.request)
			predicate = query_views._combine_predicate(the_filter, predicate, operator=operator)

		# things shared w/ me and are top level
		top_level = self.FILTER_NAMES[top_level_filter]
		def filter_shared_with(x):
			x_sharedWith = getattr(x, 'sharedWith', ())
			if self.user.username in x_sharedWith and top_level(x):
				return True
		predicate = query_views._combine_predicate(filter_shared_with, predicate, operator=operator)

		return predicate

	def getObjectsForId(self, user, ntiid):
		try:
			objects = super(_RelevantUGDView, self).getObjectsForId(user, ntiid)
		except hexc.HTTPNotFound:
			objects = ({}, {})

		result = []
		predicate = self._make_complete_predicate()
		result.extend(query_views._flatten_list_and_dicts(objects, predicate))
		return result

	def _get_items(self, ntiid, result=None):
		# query objects
		view = query_views._UGDView(self.request)
		view._DEFAULT_BATCH_SIZE = view._DEFAULT_BATCH_START = None
		try:
			all_objects = view.getObjectsForId(self.user, ntiid)
		except _hexc.HTTPNotFound:
			return ()

		result = [] if result is None else result
		predicate = self._make_complete_predicate()
		result.extend(query_views._flatten_list_and_dicts(all_objects, predicate))
		return result

	def _get_library_path(self, ntiid):
		library = self.request.registry.getUtility(lib_interfaces.IContentPackageLibrary)
		paths = library.pathToNTIID(ntiid) if library else None
		return paths[-1] if paths else None

	def _scan_quizzes(self, ntiid, result=None):
		result = [] if result is None else result
		question_map = component.queryUtility(app_interfaces.IFileQuestionMap)
		if question_map:
			path = self._get_library_path(ntiid)
			questions = question_map.by_file.get(getattr(path, 'key', None))
			for question in questions or ():
				q_ntiid = getattr(question, 'ntiid', None)
				if q_ntiid:
					self._get_items(q_ntiid, result)
		return result
	
	def _scan_videos(self, ntiid, result=None):
		result = [] if result is None else result
		video_map = component.queryUtility(app_interfaces.IVideoIndexMap)
		if video_map:
			unit = self._get_library_path(ntiid)
			u_ntiid = getattr(unit, 'ntiid', None)
			videos = video_map.by_container.get(u_ntiid)
			for video_id in videos or ():
				self._get_items(video_id, result)
		return result

	def __call__(self):
		# gather data
		items = self.getObjectsForId(self.user, self.ntiid)
		self._scan_quizzes(self.ntiid, items)
		self._scan_videos(self.ntiid, items)

		# get last modified
		LAST_MODIFIED = ext_interfaces.StandardExternalFields.LAST_MODIFIED
		lmobj = reduce(lambda x, y: x if x.lastModified > y.lastModified else y, items, self)

		# return
		result = LocatedExternalDict()
		result['Items'] = items
		result['Total'] = len(items)
		result.mimeType = nti_mimetype_with_class(None)
		result.lastModified = result[LAST_MODIFIED] = lmobj.lastModified
		interface.alsoProvides(result, app_interfaces.IUGDExternalCollection)
		return result

