#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for user dashboard

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import math
import time
import collections
from datetime import datetime

from zope import component
from zope import interface

from z3c.batching.batch import Batch

import pyramid.httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid import httpexceptions as _hexc

from nti.contentlibrary.indexed_data.interfaces import IVideoIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import IRelatedContentIndexedDataContainer

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.appserver.utils import is_true
from nti.appserver.traversal import find_interface
from nti.appserver import interfaces as app_interfaces
from nti.appserver import ugd_query_views as query_views
from nti.appserver.pyramid_authorization import is_readable

from nti.assessment.interfaces import IQAssessmentItemContainer

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver.links import Link
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.externalization.oids import to_external_oid
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.externalization import to_standard_external_created_time
from nti.externalization.externalization import to_standard_external_last_modified_time

from nti.ntiids import ntiids

from nti.utils._compat import aq_base

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

	def record(self, key, cnt=1, score=0.0):
		self.total += cnt
		self.score += score
		self.counter[key] += cnt

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

def _check_container(ntiid, user, registry=component):
	if ntiid != ntiids.ROOT:
		lib = registry.getUtility(lib_interfaces.IContentPackageLibrary)
		if (user.getContainer(ntiid) is None
			and user.getSharedContainer(ntiid, defaultValue=None) is None
			and (lib is None
				 or (getattr(lib, "pathToNTIID", None)
					 and not lib.pathToNTIID(ntiid)))):
			raise hexc.HTTPNotFound()

@interface.implementer(app_interfaces.INamedLinkView)
class _TopUserSummaryView(AbstractAuthenticatedView):

	def __init__(self, request, the_user=None, the_ntiid=None):
		super(_TopUserSummaryView, self).__init__(request)
		if self.request.context:
			self.user = the_user or self.request.context.user
			self.ntiid = the_ntiid or self.request.context.ntiid

	def _score(self, obj):
		result = 0
		sharingTargets = getattr(obj, 'sharingTargets', ())
		for st in sharingTargets or ():
			if nti_interfaces.IUser.providedBy(st):
				result += 1
			elif nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(st):
				result += 5
			elif nti_interfaces.ICommunity.providedBy(st):
				result += 10
		return result

	def _get_summary_items(self, ntiid, recurse=True):
		# query objects
		view = 	query_views._UGDAndRecursiveStreamView(self.request) \
				if recurse else query_views._UGDStreamView(self.request)
		view._DEFAULT_BATCH_SIZE = view._DEFAULT_BATCH_START = None
		try:
			all_objects = view.getObjectsForId(self.user, ntiid)
		except _hexc.HTTPNotFound:
			return ({}, {})

		# loop and collect
		seen = set()
		result = LocatedExternalDict()
		by_type = collections.defaultdict(int)
		for o in query_views._flatten_list_and_dicts(all_objects):
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
				recorder = result.get(creator)
				if recorder is None:
					result[creator] = recorder = _Recorder()
				recorder.record(mime_type, score=self._score(obj))
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
		# gather all paths for the request ntiid
		all_paths = self._get_self_and_children(self.ntiid)

		# gather all ugd in the question containers
		for unit in all_paths or ():
			for question in IQAssessmentItemContainer(unit,()):
				ntiid = getattr(question, 'ntiid', None)
				usr_map, by_type = self._get_summary_items(ntiid, False) if ntiid else ({}, {})
				self._merge_maps(total_user_map, total_by_type, usr_map, by_type)

	def _scan_related_content(self, total_user_map, total_by_type):
		# gather all paths for the request ntiid
		all_paths = self._get_self_and_children(self.ntiid)

		for content_unit in all_paths or ():
			related_content_info = IRelatedContentIndexedDataContainer(content_unit)
			for rc_entry in related_content_info.get_data_items():
				ntiid = rc_entry.get('ntiid')
				if ntiid and rc_entry.get('type') == "application/vnd.nextthought.content":
					usr_map, by_type = self._get_summary_items(ntiid, False)
					self._merge_maps(total_user_map, total_by_type, usr_map, by_type)

	def _scan_videos(self, total_user_map, total_by_type):
		# gather all paths for the request ntiid
		all_paths = self._get_self_and_children(self.ntiid)

		# gather all ugd in the video containers
		for unit in all_paths or ():
			video_container = IVideoIndexedDataContainer(unit)
			for video_data in video_container.get_data_items():
				video_id = video_data['ntiid']
				usr_map, by_type = self._get_summary_items(video_id, False)
				self._merge_maps(total_user_map, total_by_type, usr_map, by_type)

	def __call__(self):
		# gather data
		_check_container( self.ntiid, self.user )
		total_ugd, total_by_type = self._get_summary_items(self.ntiid)
		self._scan_quizzes(total_ugd, total_by_type)
		self._scan_videos(total_ugd, total_by_type)
		self._scan_related_content(total_ugd, total_by_type)

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

##### Min/Max dashboard view ####

@interface.implementer(app_interfaces.INamedLinkView)
class _UniqueMinMaxSummaryView(AbstractAuthenticatedView):

	def __init__(self, request, the_user=None, the_ntiid=None):
		super(_UniqueMinMaxSummaryView, self).__init__(request)
		if self.request.context:
			self.user = the_user or self.request.context.user
			self.ntiid = the_ntiid or self.request.context.ntiid

	def _get_cmp_value(self, obj, field):
		if field == 'lastModified':
			value = to_standard_external_last_modified_time(obj) or 0
		else:
			value = to_standard_external_created_time(obj) or 0
		return value

	def _get_summary_items(self, ntiid):
		recurse = self.request.params.get('recurse', 'False')
		recurse = str(recurse).lower() in ('true', 't', 'yes', 'y', '1')

		# query objects
		view = 	query_views._UGDView(self.request) if not recurse \
				else query_views._RecursiveUGDView(self.request)
		view._DEFAULT_BATCH_SIZE = view._DEFAULT_BATCH_START = None
		try:
			all_objects = view.getObjectsForId(self.user, ntiid)
		except _hexc.HTTPNotFound:
			return {}

		attribute = self.request.params.get('attribute', None)
		sort_on = self.request.params.get('sortOn', 'lastModified')
		sort_order = self.request.params.get('sortOrder', 'ascending')
		is_ascending = sort_order == 'ascending'
		if not attribute or sort_on not in ('lastModified', 'createdTime'):
			return {}

		seen = {}
		for o in query_views._flatten_list_and_dicts(all_objects):
			if not hasattr(o, attribute):
				continue
			key = getattr(o, attribute, None)
			if key is None:
				continue
			ref = seen.get(key)
			if ref is None:
				seen[key] = o
			else:
				o_value = self._get_cmp_value(o, sort_on)
				r_value = self._get_cmp_value(ref, sort_on)
				if is_ascending and o_value > r_value:
					seen[key] = o
				elif not is_ascending and o_value < r_value:
					seen[key] = o
		return seen

	def __call__(self):
		# gather data
		_check_container( self.ntiid, self.user )
		items = self._get_summary_items(self.ntiid)
		result = LocatedExternalDict()
		result['Items'] = list(items.values())
		result['Total'] = len(items)
		return result

##### Forum/Board TopTopic view ####

TOP_TOPICS_VIEW = u'TopTopics'

@view_config(context=frm_interfaces.IBoard)
@view_config(context=frm_interfaces.IForum)
@view_defaults(name=TOP_TOPICS_VIEW, **_r_view_defaults)
class ForumTopTopicGetView(AbstractAuthenticatedView,
						   BatchingUtilsMixin):

	_DEFAULT_DECAY = 0.94
	_DEFAULT_BATCH_SIZE = query_views._RecursiveUGDStreamView._DEFAULT_BATCH_SIZE
	_DEFAULT_BATCH_START = query_views._RecursiveUGDStreamView._DEFAULT_BATCH_START

	def __init__(self, request):
		super(ForumTopTopicGetView, self).__init__(request)
		self.now = datetime.fromtimestamp(time.time())
		self.user = find_interface(self.request.context, nti_interfaces.IEntity)

	def _score(self, topic, decay, use_hours=True):
		lm = datetime.fromtimestamp(topic.lastModified)
		delta = self.now - lm
		x = delta.days if not use_hours else delta.total_seconds() / 60 / 60
		result = math.pow(decay, x) * len(topic)
		return result

	def _get_exclude(self):
		result = set()
		param = self.request.params.get('exclude', '')
		if param:
			splits = param.split()
			result.update(splits)
		return result

	def _get_decay(self):
		decay = self.request.params.get('decay', self._DEFAULT_DECAY)
		if decay is not None:
			try:
				decay = float(decay)
				if decay <= 0 or decay > 1:
					raise _hexc.HTTPBadRequest(detail='Invalid decay factor')
			except ValueError:
				raise _hexc.HTTPBadRequest(detail='Invalid decay factor')
		return decay

	def _batch(self, mapping, result_list, batch_size=None, batch_start=None):
		if batch_size is not None and batch_start is not None:
			if batch_start >= len(result_list):
				result_list = []
			else:
				result_list = Batch(result_list, batch_start, batch_size)
				next_batch, prev_batch = result_list.next, result_list.previous
				for batch, rel in ((next_batch, 'batch-next'), (prev_batch, 'batch-prev')):
					if batch is not None and batch != result_list:
						batch_params = self.request.params.copy()
						batch_params['batchStart'] = batch.start
						link_next_href = self.request.current_route_path(_query=sorted(batch_params.items()))
						link_next = Link( link_next_href, rel=rel )
						mapping.setdefault('Links', []).append(link_next)

			mapping['Items'] = result_list
		else:
			mapping['Items'] = result_list

	def __call__(self):
		context = aq_base(self.request.context)
		if frm_interfaces.IBoard.providedBy(context):
			forums = context.values()
		else:
			forums = (context,)

		# read params
		decay = self._get_decay()
		exclude = self._get_exclude()
		batch_size, batch_start = self._get_batch_size_start()
		use_hours = is_true(self.request.params.get('useHours', False))

		# capture all topic data
		items = []
		for forum in forums:
			# check we can read the forum
			if not is_readable(forum, self.request, skip_cache=True):
				continue
			if forum.NTIID in exclude:
				continue
			for topic in forum.values():
				if not topic.NTIID in exclude:
					items.append((topic, self._score(topic, decay, use_hours)))
		items_sorted = sorted(items, key=lambda t: t[1], reverse=True)
		items = map(lambda x: x[0], items_sorted)

		# prepare output
		result = LocatedExternalDict()
		self._batch(result, items, batch_size, batch_start)
		return result

del _view_defaults
del _r_view_defaults
