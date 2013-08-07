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

from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid import httpexceptions as _hexc

from nti.appserver import _view_utils
from nti.appserver.traversal import find_interface
from nti.appserver import interfaces as app_interfaces
from nti.appserver import ugd_query_views as query_views

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.externalization.oids import to_external_oid
from nti.externalization.interfaces import LocatedExternalDict

_view_defaults = dict(route_name='objects.generic.traversal', renderer='rest')

_r_view_defaults = _view_defaults.copy()
_r_view_defaults.update(permission=nauth.ACT_READ, request_method='GET')

##### Top user dashboard view ####

def _merge_map(ref, m):
	for k, v in m.items():
		if k not in ref:
			ref[k] = v
		else:
			ref[k] = ref[k] + v

class _Recorder(object):

	__slots__ = ('score', 'total', 'counter')
	
	def __init__(self):
		self.score = 0
		self.total = 0
		self.counter = collections.defaultdict(int)
		
	def record(self, mime_type, sharingTargets=()):
		self.total += 1
		self.counter[mime_type] += 1
		s = 0
		for st in sharingTargets or ():
			if nti_interfaces.IUser.providedBy(st):
				s += 1
			elif nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(st):
				s += 5
			elif nti_interfaces.ICommunity.providedBy(st):
				s += 10
		self.score += s

	def counterMap(self):
		return LocatedExternalDict(**self.counter)

	def __str__(self):
		return "%s" % self.score

	def __repr__(self):
		return "%s(%s,%s)" % (self.__class__.__name__, self.score, self.total)

	def __iadd__(self, other):
		self.total += other.total
		self.score += other.score
		_merge_map(self.counter, other.counter)
		return self

class _TopUserSummaryView(_view_utils.AbstractAuthenticatedView):

	def __init__(self, request, the_user=None, the_ntiid=None):
		super(_TopUserSummaryView, self).__init__(request)
		if self.request.context:
			self.user = the_user or self.request.context.user
			self.ntiid = the_ntiid or self.request.context.ntiid

	def _get_summary_items(self, ntiid, recurse=True):

		# query objects
		view = query_views._UGDAndRecursiveStreamView(self.request) if recurse else query_views._UGDStreamView(self.request)
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
				sharingTargets = getattr(obj, 'flattenedSharingTargets', ())

				if creator and mime_type:
					recorder = result.get(creator)
					if recorder is None:
						result[creator] = recorder = _Recorder()
					recorder.record(mime_type, sharingTargets)
					by_type[mime_type] = by_type[mime_type] + 1

		return result, by_type
				
	def _merge_maps(self, total_user_map, total_by_type, usr_map, by_type):
		# merge by recoder objecrs
		for username, m in usr_map.items():
			recorder = total_user_map.get(username, None)
			if recorder is None:
				total_user_map[username] = m
			else:
				recorder += m

		# merge by mime_type
		_merge_map(total_by_type, by_type)

	def _get_self_and_children(self, ntiid):
		result = None
		library = self.request.registry.getUtility(lib_interfaces.IContentPackageLibrary)
		paths = library.pathToNTIID(ntiid) if library else None
		children = library.childrenOfNTIID(ntiid) if library else None
		if paths:
			result = [paths[-1]]
			result.extend(children or ())
		return result

	def _scan_quizzes(self, total_user_map, total_by_type):
		# check there are questions
		question_map = component.getUtility(app_interfaces.IFileQuestionMap)
		if not question_map:
			return

		# gather all paths for the request ntiid
		all_paths = self._get_self_and_children(self.ntiid)

		# gather all ugd in the question containers
		for unit in all_paths or ():
			questions = question_map.by_file.get(getattr(unit, 'key', None))
			for question in questions or ():
				ntiid = getattr(question, 'ntiid', None)
				usr_map, by_type = self._get_summary_items(ntiid, False) if ntiid else ({}, {})
				self._merge_maps(total_user_map, total_by_type, usr_map, by_type)
	
	def _scan_videos(self, total_user_map, total_by_type):
		video_map = component.getUtility(app_interfaces.IVideoIndexMap)
		if not video_map:
			return
		
		# gather all paths for the request ntiid
		all_paths = self._get_self_and_children(self.ntiid)

		# gather all ugd in the video containers
		for unit in all_paths or ():
			ntiid = getattr(unit, 'ntiid', None)
			videos = video_map.by_container.get(ntiid)
			for video_id in videos or ():
				usr_map, by_type = self._get_summary_items(video_id, False)
				self._merge_maps(total_user_map, total_by_type, usr_map, by_type)

	def __call__(self):
		# gather data
		total_ugd, total_by_type = self._get_summary_items(self.ntiid)
		self._scan_quizzes(total_ugd, total_by_type)
		self._scan_videos(total_ugd, total_by_type)

		# sort
		def _cmp(x,y):
			result = cmp(x[1].score, y[1].score)
			result = cmp(x[1].total, y[1].total) if result == 0 else result
			return result
		items_sorted = sorted(total_ugd.items(), cmp=_cmp, reverse=True)

		# compute
		total = 0
		items = []
		result = LocatedExternalDict()
		for k, v in items_sorted:
			entry = {'Username': k, 'Types':v.counterMap(), 'Total':v.total, 'Score':v.score}
			total += entry['Total']
			items.append(entry)
		result['Items'] = items
		result['Total'] = total
		result['Summary'] = LocatedExternalDict(total_by_type)
		return result

##### Forum/Board dashboard view ####

@view_config(context=frm_interfaces.IBoard)
@view_defaults(name="dashboard", **_r_view_defaults)
class ForumDashboardGetView(_view_utils.AbstractAuthenticatedView):

	def __init__(self, request):
		super(_TopUserSummaryView, self).__init__(request)
		self.ntiid = self.request.context.ntiid
		self.user = find_interface(self.request.context, nti_interfaces.IEntity)

	def __call__(self):
		view = query_views._UGDView(self.request)
		the_objects = view.getObjectsForId(self.user, self.ntiid)
		if not the_objects:
			raise _hexc.HTTPNotFound()


del _view_defaults
del _r_view_defaults
