#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
... $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.contentsearch.interfaces import ISearchResults

from nti.externalization.interfaces import IExternalMappingDecorator

from nti.dataserver.links import Link

@component.adapter(ISearchResults)
@interface.implementer(IExternalMappingDecorator)
class _SearchResultsLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		return bool(self._is_authenticated)
	
	def _do_decorate_external(self, original, external):
		query = original.Query
		batch_hits = getattr(original, 'Batch', None)
		if not query.IsBatching or batch_hits is None:
			return

		next_batch, prev_batch = batch_hits.next, batch_hits.previous
		for batch, rel in ((next_batch, 'batch-next'), (prev_batch, 'batch-prev')):
			if batch is not None and batch != batch_hits:
				batch_params = self.request.params.copy()
				batch_params['batchStart'] = batch.start
				params_query = sorted(batch_params.items()) # for testing
				link_next_href = self.request.current_route_path(_query=params_query)
				link_next = Link(link_next_href, rel=rel)
				external.setdefault('Links', []).append(link_next)
		# clean
		original.Batch = None
