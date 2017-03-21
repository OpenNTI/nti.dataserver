#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for relevant UGD

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.app.renderers.interfaces import IUGDExternalCollection

from nti.appserver import httpexceptions as hexc

from nti.appserver.interfaces import IContainerLeafResolver
from nti.appserver.interfaces import IContainedObjectsQuerier

from nti.appserver.ugd_query_views import _RecursiveUGDView
from nti.appserver.ugd_query_views import _combine_predicate

from nti.appserver.ugd_query_views import UGDView
from nti.appserver.ugd_query_views import Operator
from nti.appserver.ugd_query_views import lists_and_dicts_to_ext_collection

from nti.externalization.interfaces import StandardExternalFields

from nti.mimetype.mimetype import nti_mimetype_with_class

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL

union_operator = Operator.union
intersection_operator = Operator.intersection

class _AbstractRelevantUGDView(object):

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

	@classmethod
	def _get_container_leaf(clcs, ntiid):
		resolver = component.queryUtility(IContainerLeafResolver)
		return resolver.resolve(ntiid) if resolver is not None else None

	@classmethod
	def get_contained(cls, container_ntiid):
		resolver = component.queryUtility(IContainedObjectsQuerier)
		return resolver.query(container_ntiid) if resolver is not None else ()

	def get_objects(self, container_ntiid):
		# Get our nearest content unit, if available
		# Seems wrong to do this in all cases, was doing it just for
		# assessment items before.
		try:
			unit = self._get_container_leaf(container_ntiid)
			container_ntiid = unit.ntiid
		except AttributeError:
			pass
		contained_objects = self.get_contained(container_ntiid)
		contained_ntiids = set((x.ntiid for x in contained_objects))
		contained_ntiids.add(container_ntiid)

		results = []
		for ntiid in contained_ntiids:
			contained_ugd = self.getObjectsForId(self.user, ntiid)
			results.extend(contained_ugd)
		return results

	def __call__(self):
		# Gather data
		items = self.get_objects(self.ntiid)
		predicate = self._make_complete_predicate()
		# De-dupe; we could batch here if needed.
		result = lists_and_dicts_to_ext_collection(items, predicate)
		result[TOTAL] = len(result.get(ITEMS, ()))
		result.mimeType = nti_mimetype_with_class(None)
		interface.alsoProvides(result, IUGDExternalCollection)
		return result

class _RelevantUGDView(_AbstractRelevantUGDView, _RecursiveUGDView):
	"""
	A relevant view that returns UGD on our item, any contained
	objects (video, quizzes, etc), and any sub-containers.
	"""

	def getObjectsForId(self, user, ntiid):
		try:
			results = super(_RelevantUGDView, self).getObjectsForId(user, ntiid)
		except hexc.HTTPNotFound:
			results = ({}, {})
		return results

class _RelevantContainedUGDView(_AbstractRelevantUGDView, UGDView):
	"""
	A relevant view that returns UGD on our item and any contained
	objects (video, quizzes, etc), but not recursively through other
	pages/units.
	"""

	def getObjectsForId(self, user, ntiid):
		try:
			results = super(_RelevantContainedUGDView, self).getObjectsForId(user, ntiid)
		except hexc.HTTPNotFound:
			results = ({}, {})
		return results
