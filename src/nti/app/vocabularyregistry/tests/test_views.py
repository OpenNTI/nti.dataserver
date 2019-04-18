#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import has_properties
from hamcrest import instance_of
from hamcrest import is_
from hamcrest import not_
from hamcrest import none
from hamcrest import not_none
from hamcrest import same_instance
from hamcrest import contains_inanyorder

from pyramid.interfaces import IRequest

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.component.hooks import getSite

from zope.event import notify

from zope.schema.interfaces import IVocabulary
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.interfaces import IVocabularyRegistry

from nti.app.vocabularyregistry.vocabulary import Vocabulary as SimpleVocabulary
from nti.app.vocabularyregistry.vocabulary import Term as SimpleTerm

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.vocabularyregistry.utils import install_named_utility

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users import User

logger = __import__('logging').getLogger(__name__)


class _MockVocabularyFactory(object):

    def __call__(self, context):
        return component.queryUtility(IVocabulary, name='test_vocab')


class TestViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=(u'user001', u'admin001@nextthought.com'), testapp=True, default_authenticate=False)
    def test_vocabulary_read_and_delete(self):
        parent_admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        parent_admin_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'
        parent_url = 'https://alpha.nextthought.com/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab'

        child_admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        child_admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        child_url = 'https://alpha.dev/dataserver2/++etc++hostsites/alpha.dev/++etc++site/test_vocab'

        self.testapp.get(parent_url, status=404, extra_environ=parent_admin_environ)
        self.testapp.get(child_url, status=404, extra_environ=child_admin_environ)

        # create one in parent site.
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            parent_site_manager = getSite().getSiteManager()
            vocab = SimpleVocabulary([SimpleTerm(x) for x in ('a', 'b')])
            install_named_utility(vocab,
                                   utility_name=u'test_vocab',
                                   provided=IVocabulary,
                                   local_site_manager=parent_site_manager)

            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__name__, is_('test_vocab'))
            assert_that(vocab.__parent__, same_instance(parent_site_manager))

        # read in parent site.
        result = self.testapp.get(parent_url, status=200, extra_environ=parent_admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(2)}))
        assert_that([x['value'] for x in result['terms']], contains_inanyorder('a', 'b'))

        # read in child site.
        self.testapp.get(child_url, status=404, extra_environ=child_admin_environ)

        # update in parent site.
        result = self.testapp.put_json(parent_url,
                                       params={'terms': ['one', 'two', 'three']},
                                       status=200,
                                       extra_environ=parent_admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(3)}))
        assert_that([x['value'] for x in result['terms']], contains_inanyorder('one', 'two', 'three'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__name__, is_('test_vocab'))
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            assert_that([x.value for x in iter(vocab)], contains_inanyorder('one', 'two', 'three'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            child_site_manager = getSite().getSiteManager()
            assert_that(child_site_manager, not_(parent_site_manager))

            assert_that(vocab.__name__, is_('test_vocab'))
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            assert_that([x.value for x in iter(vocab)], contains_inanyorder('one', 'two', 'three'))

        # update in child site. which would create a new one in child site.
        self.testapp.put_json(child_url,
                              params={'terms': ['six']},
                              status=404,
                              extra_environ=child_admin_environ)

        # delete in child site.
        self.testapp.delete(child_url, status=404, extra_environ=child_admin_environ)

        # delete in parent site.
        self.testapp.delete(parent_url, status=204, extra_environ=parent_admin_environ)

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab, is_(None))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab, is_(None))

        # removed.
        self.testapp.delete(parent_url, status=404, extra_environ=parent_admin_environ)
