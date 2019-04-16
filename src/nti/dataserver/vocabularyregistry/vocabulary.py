#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from BTrees.OOBTree import OOTreeSet

from zope import interface

from zope.container.contained import Contained

from zope.schema.interfaces import ConstraintNotSatisfied

from nti.containers.containers import CaseInsensitiveLastModifiedBTreeContainer

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ROLE_ADMIN

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import ACE_DENY_ALL
from nti.dataserver.interfaces import ALL_PERMISSIONS
from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME

from nti.dataserver.vocabularyregistry.interfaces import IVocabularyItem
from nti.dataserver.vocabularyregistry.interfaces import IVocabularyItemContainer

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from nti.property.property import LazyOnClass

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.site.localutility import queryNextUtility


@interface.implementer(IVocabularyItem)
class VocabularyItem(SchemaConfigured, PersistentCreatedAndModifiedTimeObject, Contained):

    createDirectFieldProperties(IVocabularyItem)

    mimeType = mime_type = "application/vnd.nextthought.vocabularyregistry.vocabularyitem"

    def __init__(self, *args, **kwargs):
        # Ensure values is initialized.
        if 'values' not in kwargs:
            kwargs['values'] = ()
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedAndModifiedTimeObject.__init__(self)

    def __setattr__(self, name, value):
        if name == 'name' and self.name is not None:
            raise ConstraintNotSatisfied(u"The value of name can not be updated if it exists.", 'name')

        if name == 'values':
            _v = OOTreeSet()
            _v.update(value or ())
            value = _v
        super(VocabularyItem, self).__setattr__(name, value)

    def add(self, values):
        self.values.update(values)

    def remove(self, values):
        for x in values or ():
            self.values.remove(x)


@interface.implementer(IVocabularyItemContainer)
class VocabularyItemContainer(CaseInsensitiveLastModifiedBTreeContainer):

    @property
    def _next_vocabulary_container(self):
        return queryNextUtility(self, IVocabularyItemContainer)

    @LazyOnClass
    def __acl__(self):
        aces = [ace_allowing(ROLE_ADMIN, ALL_PERMISSIONS, type(self)),
                ace_allowing(AUTHENTICATED_GROUP_NAME, ACT_READ, type(self)),
                ACE_DENY_ALL]
        result = acl_from_aces(aces)
        return result

    def add_vocabulary_item(self, item):
        self[item.name] = item
        return item

    def delete_vocabulary_item(self, item):
        _name = getattr(item, 'name', item)
        del self[_name]

    def get_vocabulary_item(self, name, inherit=True):
        item = self.get(name, None)
        if item is None and inherit is True:
            parent = self._next_vocabulary_container
            if parent is not None:
                item = parent.get_vocabulary_item(name, inherit=inherit)
        return item

    def iterVocabularyItems(self, inherit=True):
        seen = set()
        for x in self.values():
            if x.name not in seen:
                seen.add(x.name)
                yield x

        if inherit is True:
            parent = self._next_vocabulary_container
            if parent is not None:
                for x in parent.iterVocabularyItems(inherit=inherit):
                    if x.name not in seen:
                        seen.add(x.name)
                        yield x
