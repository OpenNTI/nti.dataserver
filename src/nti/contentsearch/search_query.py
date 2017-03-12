#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component
from zope import interface

from nti.base._compat import unicode_

from nti.contentsearch.interfaces import ISearchQuery
from nti.contentsearch.interfaces import IDateTimeRange

from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured


@interface.implementer(ISearchQuery)
@component.adapter(basestring)
def _default_query_adapter(query, *args, **kwargs):
    if query is not None:
        query = QueryObject.create(query, *args, **kwargs)
    return query


@WithRepr
@EqHash('startTime', 'endTime')
@interface.implementer(IDateTimeRange)
class DateTimeRange(SchemaConfigured):
    createDirectFieldProperties(IDateTimeRange)

    mime_type = mimeType = 'application/vnd.nextthought.search.datetimerange'


@WithRepr
@EqHash('term')
@interface.implementer(ISearchQuery)
class QueryObject(SchemaConfigured):
    createDirectFieldProperties(ISearchQuery)

    __external_can_create__ = True
    __external_class_name__ = 'SearchQuery'

    mime_type = mimeType = 'application/vnd.nextthought.search.query'

    location = alias('origin')

    @property
    def query(self):
        return self.term

    @property
    def IsEmpty(self):
        return not self.term
    is_empty = IsEmpty

    @property
    def IsDescendingSortOrder(self):
        return self.sortOrder == 'descending'
    is_descending_sort_order = IsDescendingSortOrder

    def items(self):
        return self.context.items() if self.context else ()

    @property
    def IsBatching(self):
        return True if self.batchStart is not None and self.batchSize else False
    is_batching = IsBatching

    # ---------------

    @classmethod
    def create(cls, query, **kwargs):
        if isinstance(query, six.string_types):
            queryobject = QueryObject(term=query)
        else:
            if isinstance(query, QueryObject):
                if kwargs:
                    queryobject = QueryObject()
                    queryobject.__dict__.update(query.__dict__)
                else:
                    queryobject = query

        if kwargs:
            context = queryobject.context
            if context is None:
                context = queryobject.context = dict()
            for k, v in kwargs.items():
                if v is None:
                    continue
                if k in ISearchQuery:
                    setattr(queryobject, k, v)
                else:
                    v = unicode_(v) if isinstance(v, six.string_types) else v
                    context[unicode_(k)] = v
        return queryobject
