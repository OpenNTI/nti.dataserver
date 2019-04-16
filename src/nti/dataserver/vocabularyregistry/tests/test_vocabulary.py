#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from BTrees.OOBTree import OOTreeSet

from hamcrest import is_
from hamcrest import not_
from hamcrest import raises
from hamcrest import calling
from hamcrest import not_none
from hamcrest import has_key
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import instance_of
from hamcrest import same_instance
from hamcrest import has_properties
from hamcrest import contains_inanyorder

from zope import component

from zope.component.hooks import getSite

from zope.schema.interfaces import ConstraintNotSatisfied

from nti.contentfragments.interfaces import PlainTextContentFragment

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.vocabularyregistry.interfaces import IVocabularyItemContainer

from nti.dataserver.vocabularyregistry.vocabulary import VocabularyItem
from nti.dataserver.vocabularyregistry.vocabulary import VocabularyItemContainer

from nti.dataserver.vocabularyregistry.subscribers import install_site_vocabulary_container

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.externalization import internalization

from nti.externalization.externalization import toExternalObject


class TestVocabulary(DataserverLayerTest):

    def _internalize(self, external):
        factory = internalization.find_factory_for(external)
        assert_that(factory, is_(not_none()))
        new_io = factory()
        internalization.update_from_external_object(new_io, external)
        return new_io

    @WithMockDSTrans
    def test_vocabulary_item(self):
        # Both name and values are required.
        item = VocabularyItem(name=u'xyz')
        assert_that(item.values, instance_of(OOTreeSet))
        assert_that(item.values, has_length(0))

        # add
        item.add([u'a', u'b'])
        assert_that(item.values, contains_inanyorder('a', 'b'))

        item.add([u'a', u'b', u'c', u'd'])
        assert_that(item.values, contains_inanyorder('a', 'b', 'c', 'd'))

        # remove
        item.remove(['a', 'b'])
        assert_that(item.values, contains_inanyorder('c', 'd'))

        item.remove(['c', 'd'])
        assert_that(item.values, has_length(0))

        assert_that(calling(item.remove).with_args(['e']), raises(KeyError))

        # internalizing/externalizing
        item = VocabularyItem(name=u'first', values=(u'one', u'two'))
        assert_that(item.values, instance_of(OOTreeSet))
        assert_that(item, has_properties({'name': 'first', 'values': contains_inanyorder('one','two')}))

        assert_that(calling(setattr).with_args(item, 'name', u'updatedname'), raises(ConstraintNotSatisfied))

        external = toExternalObject(item)
        assert_that(external,
                    has_entries({'name': 'first',
                                 'values': contains_inanyorder('one', 'two'),
                                 'Class': 'VocabularyItem',
                                 'MimeType': 'application/vnd.nextthought.vocabularyregistry.vocabularyitem'}))

        obj = self._internalize(external)
        assert_that(obj.values, instance_of(OOTreeSet))
        assert_that(obj, has_properties({'name': u'first',
                                         'values': contains_inanyorder('one', 'two')}))

    @WithMockDSTrans
    def test_vocabulary_item_container(self):
        folder = VocabularyItemContainer()
        connection = mock_dataserver.current_transaction
        connection.add(folder)

        item = VocabularyItem(name=u'first', values=(u'one', u'two'))
        assert_that(item.__parent__, is_(None))

        folder.add_vocabulary_item(item)

        items = [x for x in folder.values()]
        assert_that(items, has_length(1))
        assert_that(item.__parent__, same_instance(folder))

        result = folder.get_vocabulary_item(item.name)
        assert_that(result, same_instance(item))
        assert_that(result.__parent__, same_instance(folder))

        assert_that(calling(folder.add_vocabulary_item).with_args(VocabularyItem(name=u'first', values=(u'one', u'two'))), raises(KeyError))

        folder.delete_vocabulary_item(item)
        items = [x for x in folder.values()]
        assert_that(items, has_length(0))
        assert_that(item.__parent__, is_(None))

        assert_that(calling(folder.delete_vocabulary_item).with_args(item), raises(KeyError))

    @WithMockDSTrans
    def test_vocabulary_item_container_utility(self):
        # we don't have one unless we install in a specific site.
        container = component.queryUtility(IVocabularyItemContainer)
        assert_that(container, is_(None))

        site_mgr = getSite().getSiteManager()
        assert_that(site_mgr, not_(has_key('Vocabularies')))

        # install
        assert_that(getSite().__name__, is_('dataserver2'))
        install_site_vocabulary_container(site_mgr)

        container = component.queryUtility(IVocabularyItemContainer)
        assert_that(container, not_none())
        assert_that(container.__name__, is_(u'Vocabularies'))
        assert_that(container.__parent__, same_instance(site_mgr))

        assert_that(site_mgr, has_key('Vocabularies'))
        assert_that(site_mgr['Vocabularies'], same_instance(container))
