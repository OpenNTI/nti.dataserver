#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import contains_inanyorder

from zope import interface
from zope import component

from zope.component import getGlobalSiteManager

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.vocabularyregistry.interfaces import IVocabularyItemContainer
from nti.dataserver.vocabularyregistry.vocabulary import VocabularyItem

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.users import User


class TestViews(ApplicationLayerTest):

    def setUp(self):
        self.admin_environ = self._make_extra_environ(username='test@nextthought.com')
        self.admin_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'

        self.user_environ = self._make_extra_environ(username=u'user001')
        self.user_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'

        self.anonymous_environ = self._make_extra_environ(username=None)
        self.anonymous_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'

    @WithSharedApplicationMockDS(users=(u'user001', u'test@nextthought.com'), testapp=True, default_authenticate=False)
    def testGetVocabulariesView(self):
        url = '/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/Vocabularies'
        self.testapp.get(url, status=401, extra_environ=self.anonymous_environ)
        self.testapp.get(url, status=200, extra_environ=self.user_environ)
        res = self.testapp.get(url, status=200, extra_environ=self.admin_environ).json_body
        assert_that(res, has_entries({'Total': 0, 'ItemCount': 0, 'Items': has_length(0)}))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            container = component.getUtility(IVocabularyItemContainer)
            container.add_vocabulary_item(VocabularyItem(name=u'first', values=(u'a', u'b')))
            container.add_vocabulary_item(VocabularyItem(name=u'second', values=(u'c', u'd')))

        res = self.testapp.get(url, status=200, extra_environ=self.admin_environ).json_body
        assert_that(res, has_entries({'Total': 2, 'ItemCount': 2, 'Items': has_length(2)}))

        # child
        child_url = '/dataserver2/++etc++hostsites/alpha.dev/++etc++site/Vocabularies'
        res = self.testapp.get(child_url, status=200, extra_environ=self.admin_environ).json_body
        assert_that(res, has_entries({'Total': 2, 'ItemCount': 2, 'Items': has_length(2)}))

        res = self.testapp.get(child_url, params={'inherit': 'false'}, status=200, extra_environ=self.admin_environ).json_body
        assert_that(res, has_entries({'Total': 0, 'ItemCount': 0, 'Items': has_length(0)}))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            container = component.getUtility(IVocabularyItemContainer)
            # get_vocabulary_item
            assert_that(container.get_vocabulary_item('first'), is_not(None))
            assert_that(container.get_vocabulary_item('first', inherit=False), is_(None))

            container.add_vocabulary_item(VocabularyItem(name=u'first', values=(u'ef',)))
            container.add_vocabulary_item(VocabularyItem(name=u'third', values=(u'ok',)))

            assert_that(container.get_vocabulary_item('first').values, contains_inanyorder('ef'))
            assert_that(container.get_vocabulary_item('first', inherit=False).values, contains_inanyorder('ef'))

            # iterVocabularyItems
            items = [x for x in container.iterVocabularyItems()]
            assert_that(items, has_length(3))
            assert_that([x.name for x in items], contains_inanyorder('first', 'second', 'third'))
            assert_that([x.values for x in items if x.name=='first'][0], contains_inanyorder('ef'))

            items = [x for x in container.iterVocabularyItems(inherit=False)]
            assert_that(items, has_length(2))
            assert_that([x.name for x in items], contains_inanyorder('first', 'third'))

        res = self.testapp.get(child_url, status=200, extra_environ=self.admin_environ).json_body
        assert_that(res, has_entries({'Total': 3, 'ItemCount': 3, 'Items': has_length(3)}))

        res = self.testapp.get(child_url+'?inherit=false', status=200, extra_environ=self.admin_environ).json_body
        assert_that(res, has_entries({'Total': 2, 'ItemCount': 2, 'Items': has_length(2)}))

        # other
        other_site_url = '/dataserver2/++etc++hostsites/demo.dev/++etc++site/Vocabularies'
        res = self.testapp.get(other_site_url, status=200, extra_environ=self.admin_environ).json_body
        assert_that(res, has_entries({'Total': 0, 'ItemCount': 0, 'Items': has_length(0)}))

    @WithSharedApplicationMockDS(users=(u'user001', u'test@nextthought.com'), testapp=True, default_authenticate=False)
    def test_vocabulary_crud(self):
        url = '/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/Vocabularies'
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            container = component.getUtility(IVocabularyItemContainer)
            assert_that(container, has_length(0))

        params = {'name': u'first',
                  'values': [u'a', u'b'],
                  'MimeType': 'application/vnd.nextthought.vocabularyregistry.vocabularyitem'}

        # create
        self.testapp.post_json(url, params=params, status=401, extra_environ=self.anonymous_environ)
        self.testapp.post_json(url, params=params, status=403, extra_environ=self.user_environ)
        res = self.testapp.post_json(url, params=params, status=201, extra_environ=self.admin_environ).json_body
        assert_that(res, has_entries({'name': 'first',
                                      'values': contains_inanyorder('a', 'b'),
                                      'MimeType': 'application/vnd.nextthought.vocabularyregistry.vocabularyitem'}))
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            container = component.getUtility(IVocabularyItemContainer)
            assert_that(container, has_length(1))

        res = self.testapp.post_json(url, params=params, status=409, extra_environ=self.admin_environ).json_body
        assert_that(res['message'], is_('Vocabulary exists.'))

        # read
        voca_url = url + '/first'
        self.testapp.get(voca_url, status=401, extra_environ=self.anonymous_environ)
        res = self.testapp.get(voca_url, status=200, extra_environ=self.user_environ).json_body
        assert_that(res, has_entries({'name': 'first',
                                      'values': contains_inanyorder('a', 'b'),
                                      'MimeType': 'application/vnd.nextthought.vocabularyregistry.vocabularyitem'}))
        self.forbid_link_with_rel(res, 'add')
        self.forbid_link_with_rel(res, 'remove')

        res = self.testapp.get(voca_url, status=200, extra_environ=self.admin_environ).json_body
        assert_that(res, has_entries({'name': 'first',
                                      'values': contains_inanyorder('a', 'b'),
                                      'MimeType': 'application/vnd.nextthought.vocabularyregistry.vocabularyitem'}))
        self.require_link_href_with_rel(res, 'add')
        self.require_link_href_with_rel(res, 'remove')

        # delete
        self.testapp.delete(voca_url, status=401, extra_environ=self.anonymous_environ)
        self.testapp.delete(voca_url, status=403, extra_environ=self.user_environ)
        self.testapp.delete(voca_url, status=204, extra_environ=self.admin_environ)
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            container = component.getUtility(IVocabularyItemContainer)
            assert_that(container, has_length(0))

    @WithSharedApplicationMockDS(users=(u'user001', u'test@nextthought.com'), testapp=True, default_authenticate=False)
    def test_values_add_and_remove_views(self):
        url = '/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/Vocabularies'
        params = {'name': u'first',
                  'MimeType': 'application/vnd.nextthought.vocabularyregistry.vocabularyitem'}
        res = self.testapp.post_json(url, params=params, status=201, extra_environ=self.admin_environ).json_body

        add_url = url + '/first/@@add'
        params = ['one', 'two']

        self.testapp.post_json(add_url, params=params, status=401, extra_environ=self.anonymous_environ)
        self.testapp.post_json(add_url, params=params, status=403, extra_environ=self.user_environ)
        self.testapp.post_json(add_url, params=params, status=200, extra_environ=self.admin_environ)
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            container = component.getUtility(IVocabularyItemContainer)
            item = container.get_vocabulary_item('first')
            assert_that(item.values, contains_inanyorder('one', 'two'))

        self.testapp.post_json(add_url, params=['three'], status=200, extra_environ=self.admin_environ)
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            assert_that(item.values, contains_inanyorder('one', 'two', 'three'))

        remove_url = url + '/first/@@remove'
        params = ['two']
        self.testapp.post_json(remove_url, params=params, status=401, extra_environ=self.anonymous_environ)
        self.testapp.post_json(remove_url, params=params, status=403, extra_environ=self.user_environ)
        self.testapp.post_json(remove_url, params=params, status=200, extra_environ=self.admin_environ)
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            assert_that(item.values, contains_inanyorder('one', 'three'))

        self.testapp.post_json(remove_url, params=['one', 'three'], status=200, extra_environ=self.admin_environ)
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            assert_that(item.values, has_length(0))
