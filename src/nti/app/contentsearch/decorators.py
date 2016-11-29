#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.contentsearch.interfaces import ISearchResults

from nti.externalization.interfaces import IExternalMappingDecorator

@component.adapter(ISearchResults)
@interface.implementer(IExternalMappingDecorator)
class _SearchResultsDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _do_decorate_external(self, context, external):
		query = context.Query
		if query is not None and query.IsBatching:
			batchSize, batchStart = query.batchSize, query.batchStart
			if len(context) > 0:
				prev_batch_start, next_batch_start = \
						BatchingUtilsMixin._batch_start_tuple(batchStart, batchSize)
				BatchingUtilsMixin._create_batch_links(self.request, 
													   external,
 										 			   next_batch_start, 
 										 			   prev_batch_start)
