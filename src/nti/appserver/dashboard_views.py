#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for user dashboard

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections

from zope import component

import pyramid.httpexceptions as _hexc

from nti.appserver import _view_utils

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.oids import to_external_oid
from nti.externalization.interfaces import LocatedExternalDict

from . import interfaces as app_interfaces
from . import ugd_query_views as query_views

class _TopUserSummaryView(_view_utils.AbstractAuthenticatedView):

	def __init__( self, request, the_user=None, the_ntiid=None ):
		super(_TopUserSummaryView,self).__init__( request )
		if self.request.context:
			self.user = the_user or self.request.context.user
			self.ntiid = the_ntiid or self.request.context.ntiid

	def _get_summary_items(self, ntiid, recurse=True):

		# query objects
		view = query_views._UGDAndRecursiveStreamView(self.request) if recurse else query_views._UGDView(self.request)
		view._DEFAULT_BATCH_SIZE = view._DEFAULT_BATCH_START = None
		try:
			all_objects = view.getObjectsForId(self.user, ntiid)
		except _hexc.HTTPNotFound:
			return ({}, {})

		# loop and collect
		seen = set()
		by_type = collections.defaultdict(int)
		result = LocatedExternalDict()
		for iterable in all_objects:
			try:
				to_iter = iterable.itervalues()
			except (AttributeError, TypeError):
				to_iter = iterable

			for o in to_iter or ():
				# check for model content and Change events
				if 	nti_interfaces.IStreamChangeEvent.providedBy(o) and \
					o.type in (nti_interfaces.SC_CREATED, nti_interfaces.SC_MODIFIED):
					obj = o.object
				elif nti_interfaces.IModeledContent.providedBy(o):
					obj = o
				else:
					continue

				oid = to_external_oid(obj)
				if oid in seen:
					continue

				seen.add(oid)
				creator = getattr(obj, 'creator', None)
				creator = getattr(creator, 'username', creator)
				mime_type = getattr(obj, "mimeType", getattr(obj, "mime_type", None))

				if creator and mime_type:
					counter = result.get(creator)
					if counter is None:
						result[creator] = counter = LocatedExternalDict()
					if mime_type not in counter:
						counter[mime_type] = 1
					else:
						counter[mime_type] = counter[mime_type] + 1
					by_type[mime_type] = by_type[mime_type] + 1

		return result, by_type

	def _merge_map(self, total, m):
		# merge by mime_type
		for k, v in m.items():
			if k not in total:
				total[k] = v
			else:
				total[k] = total[k] + v
				
	def _merge_maps(self, total_user_map, total_by_type, usr_map, by_type):
		# merge by user
		for username, m in usr_map.items():
			counter = total_user_map.get(username, None)
			if counter is None:
				total_user_map[username] = m
			else:
				self._merge_map(counter, m)

		# merge by mime_type
		self._merge_map(total_by_type, by_type)

	def _scan_quizzes(self, total_user_map, total_by_type):
		# check there are questions
		question_map = component.getUtility(app_interfaces.IFileQuestionMap)
		if not question_map:
			return

		# gather all paths for the request ntiid
		library = self.request.registry.getUtility(lib_interfaces.IContentPackageLibrary)
		paths = library.pathToNTIID(self.ntiid) if library else None
		children = library.childrenOfNTIID(self.ntiid) if library else None

		if not paths:
			return

		# gather all ugd in the question containers
		all_paths = [paths[-1]]
		all_paths.extend(children or ())
		for unit in all_paths:
			questions = question_map.by_file.get(getattr(unit, 'key', None))
			for question in questions or ():
				ntiid = getattr(question, 'containerId', None) or getattr(question, 'ntiid', None)
				usr_map, by_type = self._get_summary_items(ntiid, False) if ntiid else ({}, {})
				self._merge_maps(total_user_map, total_by_type, usr_map, by_type)

	def __call__( self ):
		# gather data
		total_ugd, total_by_type = self._get_summary_items(self.ntiid)
		self._scan_quizzes(total_ugd, total_by_type)

		# sort
		items_sorted = sorted(total_ugd.items(), key=lambda e: sum(e[1].values()), reverse=True)

		# compute
		total = 0
		items = []
		result = LocatedExternalDict()
		for k, v in items_sorted:
			entry = {'Username': k, 'Types':v, 'Total':sum(v.values())}
			total += entry['Total']
			items.append(entry)
		result['Items'] = items
		result['Total'] = total
		result['Summary'] = LocatedExternalDict(total_by_type)
		return result
