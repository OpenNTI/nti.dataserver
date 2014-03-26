#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for building digest emails.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.dataserver.interfaces import IUser
from nti.app.notabledata.interfaces import IUserNotableData

from itertools import groupby
from collections import namedtuple

_ContentObjectTypeDetails = namedtuple('_ContentObjectTypeDetails',
									   ('mime_type', 'count', 'most_recent'))

@component.adapter(IUser, interface.Interface)
class DigestEmailCollector(object):

	def __init__(self, context, request):
		self.remoteUser = context
		self.request = request


	def __call__(self):

		notable_data = component.getMultiAdapter( (self.remoteUser, self.request),
												  IUserNotableData)

		notable_intids_since_last_viewed = notable_data.get_notable_intids(min_created_time=notable_data.lastViewed)
		if not notable_intids_since_last_viewed:
			# Hooray, nothing to do
			return

		# We need to group them by type in order to provide group summaries,
		# but we only want to display the complete information
		# about the first (most recent) item in each group
		# TODO: There should be heuristics around that, it should be the
		# first, most notable, thing

		# So first we sort them by created time, descending.
		sorted_by_time = notable_data.sort_notable_intids(notable_intids_since_last_viewed,
														  reverse=True,
														  reify=True)

		# Then we can sort them by type, trusting the stable sort to preserve
		# relative creation times among items of the same type
		# (TODO: Is this actually guaranteed stable? If not we need our own stable implementation)
		sorted_by_type_time = notable_data.sort_notable_intids(sorted_by_time,
															   field_name='mimeType',
															   reify=True )

		# Now iterate to get the actual content objects
		# (Note that grade objects are going to have a `change` content type, which is
		# unique)
		content_objects_by_type = dict()
		for mime_type, objects in groupby( notable_data.iter_notable_intids(sorted_by_type_time),
										   key=lambda x: x.mimeType):
			content_objects_by_type[mime_type] = list(objects)

		details_by_type = dict()
		for mime_type, objects in content_objects_by_type.items():
			details_by_type[mime_type] = _ContentObjectTypeDetails(mime_type, len(objects), objects[0])
