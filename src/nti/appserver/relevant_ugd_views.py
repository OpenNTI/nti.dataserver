#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for relevant UGD

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface
from zope import component

from pyramid import httpexceptions as _hexc

from nti.app.renderers.interfaces import IUGDExternalCollection

from nti.appserver import httpexceptions as hexc
from nti.appserver import ugd_query_views as query_views

from nti.assessment.interfaces import IQAssessmentItemContainer

from nti.contentlibrary import interfaces as lib_interfaces
from nti.contentlibrary.indexed_data.interfaces import IVideoIndexedDataContainer

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import LocatedExternalList

from nti.mimetype.mimetype import nti_mimetype_with_class

LAST_MODIFIED = ext_interfaces.StandardExternalFields.LAST_MODIFIED

union_operator = query_views.Operator.union
intersection_operator = query_views.Operator.intersection

def _flatten_list_and_dicts(result, lists_and_dicts, predicate=None):
	lastMod = getattr(result, 'lastModified', 0)
	for list_or_dict in lists_and_dicts:
		if list_or_dict is None:
			continue
		try:
			lastMod = max(lastMod, list_or_dict.lastModified)
		except AttributeError:
			pass
		try:
			to_iter = list_or_dict.itervalues()
			lastMod = max(lastMod, list_or_dict.get('Last Modified', 0))
		except (AttributeError, TypeError):
			to_iter = list_or_dict

		for item in to_iter:
			if item is not None and (predicate is None or predicate(item)):
				result.append(item)  # add to list
				lastMod = max(lastMod, getattr(item, 'lastModified', 0))
	result.lastModified = lastMod

class _RelevantUGDView(query_views._UGDView):

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
			predicate = query_views._combine_predicate(the_filter,
													   predicate,
													   operator=operator)

		# things shared w/ me and are top level
		top_level = self.FILTER_NAMES[top_level_filter]
		def filter_shared_with(x):
			x_sharedWith = getattr(x, 'sharedWith', ())
			if self.user.username in x_sharedWith and top_level(x):
				return True
		predicate = query_views._combine_predicate(filter_shared_with,
												   predicate,
												   operator=operator)

		return predicate

	def getObjectsForId(self, user, ntiid):
		try:
			objects = super(_RelevantUGDView, self).getObjectsForId(user, ntiid)
		except hexc.HTTPNotFound:
			objects = ({}, {})

		result = LocatedExternalList()
		predicate = self._make_complete_predicate()
		_flatten_list_and_dicts(result, objects, predicate)
		return result

	def _get_items(self, ntiid, result=None):
		# query objects
		view = query_views._UGDView(self.request)
		view._DEFAULT_BATCH_SIZE = view._DEFAULT_BATCH_START = None
		try:
			all_objects = view.getObjectsForId(self.user, ntiid)
		except _hexc.HTTPNotFound:
			return ()

		result = LocatedExternalList() if result is None else result
		predicate = self._make_complete_predicate()
		_flatten_list_and_dicts(result, all_objects, predicate)
		return result

	def _get_library_path(self, ntiid):
		library = component.getUtility(lib_interfaces.IContentPackageLibrary)
		paths = library.pathToNTIID(ntiid) if library else None
		return paths[-1] if paths else None

	def _scan_quizzes(self, ntiid, result=None):
		result = LocatedExternalList() if result is None else result
		library = component.getUtility(lib_interfaces.IContentPackageLibrary)
		# quizzes are often subcontainers, so we look at the parent
		# and its children
		ntiids = set()
		for unit in library.childrenOfNTIID(ntiid) + [self._get_library_path(ntiid)]:
			for asm_item in IQAssessmentItemContainer(unit, ()):
				q_ntiid = getattr(asm_item, 'ntiid', None)
				if q_ntiid and q_ntiid not in ntiids:
					ntiids.add(q_ntiid)
					self._get_items(q_ntiid, result)
		return result

	def _scan_videos(self, ntiid, result=None):
		result = LocatedExternalList() if result is None else result
		unit = self._get_library_path(ntiid)
		if unit is not None:
			for video_data in IVideoIndexedDataContainer(unit).get_data_items():
				video_id = video_data['ntiid']
				self._get_items(video_id, result)
		return result

	def __call__(self):
		# gather data
		items = self.getObjectsForId(self.user, self.ntiid)
		self._scan_quizzes(self.ntiid, items)
		self._scan_videos(self.ntiid, items)

		# return
		result = LocatedExternalDict()
		result['Items'] = items
		result['Total'] = len(items)
		result.mimeType = nti_mimetype_with_class(None)
		result.lastModified = result[LAST_MODIFIED] = items.lastModified
		interface.alsoProvides(result, IUGDExternalCollection)
		return result
