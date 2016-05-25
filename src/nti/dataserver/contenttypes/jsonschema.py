#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: jsonschema.py 88705 2016-05-16 18:00:32Z carlos.sanchez $
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.coremetadata.interfaces import IObjectJsonSchemaMaker

from nti.coremetadata.jsonschema import CoreJsonSchemafier

from nti.dataserver.interfaces import INote

from nti.externalization.interfaces import LocatedExternalDict

FIELDS = 'Fields'
ACCEPTS = 'Accepts'

class NoteJsonSchemafier(CoreJsonSchemafier):
	
	def allow_field(self, name, field):
		if name in ('id', 'sharingTargets', 'flattenedSharingTargets',
					'flattenedSharingTargetNames'):
			return False
		return super(NoteJsonSchemafier, self).allow_field(name, field)

	def post_process_field(self, name, field, item_schema):
		super(NoteJsonSchemafier, self).post_process_field(name, field, item_schema)

		if name in ('sharedWith','tags'):
			item_schema['base_type'] = 'string'
			item_schema['type'] = 'List'
		elif name == 'title':
			item_schema['type'] = 'List'
		elif name == 'inReplyTo':
			item_schema['base_type'] = 'string'
			item_schema['type'] = 'string'
		elif name == 'inReplyTo':
			item_schema['base_type'] = 'string'
			item_schema['type'] = 'string'

@interface.implementer(IObjectJsonSchemaMaker)
class NoteJsonSchemaMaker(object):

	maker = NoteJsonSchemafier

	def make_schema(self, schema=INote):
		result = LocatedExternalDict()
		maker = self.maker(schema)
		result[FIELDS] = maker.make_schema()
		return result
