#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for relevant UGD

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from itertools import chain

from zope import component
from zope import interface

from pyramid import httpexceptions as _hexc

from nti.app.renderers.interfaces import IUGDExternalCollection

from nti.appserver import httpexceptions as hexc
from nti.appserver.ugd_query_views import Operator
from nti.appserver.ugd_query_views import _UGDView
from nti.appserver.ugd_query_views import _combine_predicate

from nti.assessment.interfaces import IQAssessmentItemContainer

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.indexed_data.interfaces import IVideoIndexedDataContainer

from nti.externalization.interfaces import StandardExternalFields

from nti.mimetype.mimetype import nti_mimetype_with_class

from .ugd_query_views import lists_and_dicts_to_ext_collection

LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED

union_operator = Operator.union
intersection_operator = Operator.intersection

class _RelevantUGDView(_UGDView):

	def _make_accept_predicate(self):
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
			predicate = _combine_predicate(the_filter, predicate, operator=operator)

		# things shared w/ me and are top level
		top_level = self.FILTER_NAMES[top_level_filter]
		def filter_shared_with(x):
			x_sharedWith = getattr(x, 'sharedWith', ())
			if self.user.username in x_sharedWith and top_level(x):
				return True
		predicate = _combine_predicate(filter_shared_with, predicate, operator=operator)
		return predicate

	def getObjectsForId(self, user, ntiid):
		try:
			results = super(_RelevantUGDView, self).getObjectsForId(user, ntiid)
		except hexc.HTTPNotFound:
			results = ({}, {})
		return results

	def _get_items(self, ntiid):
		# query objects
		view = _UGDView(self.request)
		view._DEFAULT_BATCH_SIZE = view._DEFAULT_BATCH_START = None
		try:
			results = view.getObjectsForId(self.user, ntiid)
		except _hexc.HTTPNotFound:
			results = ()
		return results

	def _get_library_path(self, ntiid):
		library = component.getUtility(IContentPackageLibrary)
		paths = library.pathToNTIID(ntiid) if library else None
		return paths[-1] if paths else None

	def _scan_quizzes(self, ntiid):
		library = component.getUtility(IContentPackageLibrary)
		# quizzes are often subcontainers, so we look at the parent and its children
		ntiids = set()
		results = []
		for unit in library.childrenOfNTIID(ntiid) + [self._get_library_path(ntiid)]:
			for asm_item in IQAssessmentItemContainer(unit, ()):
				q_ntiid = getattr(asm_item, 'ntiid', None)
				if q_ntiid and q_ntiid not in ntiids:
					ntiids.add(q_ntiid)
					items = self._get_items(q_ntiid)
					if items:
						results.extend(items)
		return results

	def _scan_videos(self, ntiid):
		unit = self._get_library_path(ntiid)
		results = []
		if unit is not None:
			for video_data in IVideoIndexedDataContainer(unit).values():
				video_id = video_data.ntiid
				items = self._get_items(video_id)
				if items:
					results.extend(items)
		return results

	def __call__(self):
		# Gather data
		items = self.getObjectsForId(self.user, self.ntiid)
		quiz_items = self._scan_quizzes(self.ntiid)
		video_items = self._scan_videos(self.ntiid)

		predicate = self._make_complete_predicate()
		all_items = chain(items, quiz_items, video_items)
		# De-dupe; we could batch here if needed.
		result = lists_and_dicts_to_ext_collection(all_items, predicate)
		result['Total'] = len(result.get('Items', ()))
		result.mimeType = nti_mimetype_with_class(None)
		interface.alsoProvides(result, IUGDExternalCollection)
		return result
