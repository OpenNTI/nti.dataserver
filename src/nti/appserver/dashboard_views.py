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

from nti.appserver import _view_utils

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.oids import to_external_oid
from nti.externalization.interfaces import LocatedExternalDict

from .ugd_query_views import _UGDAndRecursiveStreamView

class _TopUserSummaryView(_view_utils.AbstractAuthenticatedView):

	def __init__( self, request, the_user=None, the_ntiid=None ):
		super(_TopUserSummaryView,self).__init__( request )
		if self.request.context:
			self.user = the_user or self.request.context.user
			self.ntiid = the_ntiid or self.request.context.ntiid

	def __call__( self ):
		# query objects
		view = _UGDAndRecursiveStreamView(self.request)
		view._DEFAULT_BATCH_SIZE = view._DEFAULT_BATCH_START = None
		all_objects = view.getObjectsForId(self.user, self.ntiid)

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
				if nti_interfaces.IStreamChangeEvent.providedBy(o) and o.type in (nti_interfaces.SC_CREATED, nti_interfaces.SC_MODIFIED):
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
		# sort
		items_sorted = sorted(result.items(), key=lambda e: sum(e[1].values()), reverse=True)

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
		result['Summary'] = LocatedExternalDict(by_type)
		return result
