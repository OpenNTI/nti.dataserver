#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: jsonschema.py 88705 2016-05-16 18:00:32Z carlos.sanchez $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.base._compat import text_

from nti.coremetadata.interfaces import IObjectJsonSchemaMaker

from nti.coremetadata.jsonschema import CoreJsonSchemafier

from nti.dataserver.interfaces import INote

from nti.externalization.interfaces import LocatedExternalDict

FIELDS = u'Fields'
ACCEPTS = u'Accepts'

logger = __import__('logging').getLogger(__name__)


class NoteJsonSchemafier(CoreJsonSchemafier):

    def allow_field(self, name, field):
        if name in ('id', 'sharingTargets', 'flattenedSharingTargets',
                    'flattenedSharingTargetNames', 'references'):
            return False
        return super(NoteJsonSchemafier, self).allow_field(name, field)

    def post_process_field(self, name, field, item_schema):
        super(NoteJsonSchemafier, self).post_process_field(name, field, item_schema)

        if name in ('sharedWith', 'tags', 'mentions'):
            item_schema['base_type'] = 'string'
            item_schema['type'] = 'List'
        elif name == 'title':
            item_schema['type'] = 'string'
        elif name == 'inReplyTo':
            item_schema['base_type'] = 'string'
            item_schema['type'] = 'string'
        elif name == 'applicableRange':
            item_schema['base_type'] = 'application/vnd.nextthought.contentrange.contentrangedescription'
            item_schema['type'] = 'Object'
        elif name == 'presentationProperties':
            item_schema['base_type'] = 'string'
            item_schema['type'] = 'Dict'
        elif name == 'body':
            types = set(item_schema['base_type'])
            types.discard('named')
            types.add('namedfile')
            item_schema['base_type'] = [
                text_(x) for x in sorted(types, reverse=True)
            ]
            item_schema['type'] = 'List'


@interface.implementer(IObjectJsonSchemaMaker)
class NoteJsonSchemaMaker(object):

    maker = NoteJsonSchemafier

    def make_schema(self, schema=INote, unused_user=None):
        result = LocatedExternalDict()
        maker = self.maker(schema)
        result[FIELDS] = maker.make_schema()
        return result
