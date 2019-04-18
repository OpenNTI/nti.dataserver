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

from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users import User

logger = __import__('logging').getLogger(__name__)


class _MockVocabularyFactory(object):

    def __call__(self, context):
        return component.queryUtility(IVocabulary, name='test_vocab')


class TestViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=(u'user001', u'admin001@nextthought.com'), testapp=True, default_authenticate=False)
    def testVocabularyCreationView(self):
        # no persistent vocabulary/factory
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            vocab = component.queryUtility(IVocabulary, name=u'test_vocab')
            assert_that(vocab, same_instance(None))
            factory = component.queryUtility(IVocabularyFactory, name=u'test_vocab')
            assert_that(factory, same_instance(None))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            vocab = component.queryUtility(IVocabulary, name=u'test_vocab')
            assert_that(vocab, same_instance(None))
            factory = component.queryUtility(IVocabularyFactory, name=u'test_vocab')
            assert_that(factory, same_instance(None))

        # register for parent site.
        admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'
        url = 'https://alpha.nextthought.com/dataserver2/++etc++vocabularies'

        params = {'name': 'test_vocab', 'terms': ['one', 'two']}
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(2)}))
        assert_that([x['value'] for x in result['terms']], contains_inanyorder('one', 'two'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            parent_site_manager = getSite().getSiteManager()
            vocab = component.queryUtility(IVocabulary, name=u'test_vocab')
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            factory = component.queryUtility(IVocabularyFactory, name=u'test_vocab')
            assert_that(factory.__parent__, same_instance(parent_site_manager))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            # child inherits from parent
            child_site_manager = getSite().getSiteManager()
            assert_that(child_site_manager, not_(parent_site_manager))

            vocab = component.queryUtility(IVocabulary, name=u'test_vocab')
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            factory = component.queryUtility(IVocabularyFactory, name=u'test_vocab')
            assert_that(factory.__parent__, same_instance(parent_site_manager))

        # child site
        admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        url = 'https://alpha.dev/dataserver2/++etc++vocabularies'

        # read
        result = self.testapp.get(url+'/test_vocab', params=params, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(2)}))
        assert_that([x['value'] for x in result['terms']], contains_inanyorder('one', 'two'))

        # create/read
        params = {'name': 'test_vocab', 'terms': ['three', 'four', 'five']}
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(3)}))

        result = self.testapp.get(url+'/test_vocab', params=params, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(3)}))
        assert_that([x['value'] for x in result['terms']], contains_inanyorder('three', 'four', 'five'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            vocab = component.queryUtility(IVocabulary, name=u'test_vocab')
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            factory = component.queryUtility(IVocabularyFactory, name=u'test_vocab')
            assert_that(factory.__parent__, same_instance(parent_site_manager))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            vocab = component.queryUtility(IVocabulary, name=u'test_vocab')
            assert_that(vocab.__parent__, same_instance(child_site_manager))
            factory = component.queryUtility(IVocabularyFactory, name=u'test_vocab')
            assert_that(factory.__parent__, same_instance(child_site_manager))

        # create/read
        params = {'name': 'test_vocab', 'terms': ['six']}
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(1)}))
        assert_that([x['value'] for x in result['terms']], contains_inanyorder('six'))

        result = self.testapp.get(url+'/test_vocab', params=params, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(1)}))
        assert_that([x['value'] for x in result['terms']], contains_inanyorder('six'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            vocab = component.queryUtility(IVocabulary, name=u'test_vocab')
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            assert_that(vocab.__name__, is_('test_vocab'))
            assert_that([x.value for x in iter(vocab)], contains_inanyorder('one', 'two'))
            factory = component.queryUtility(IVocabularyFactory, name=u'test_vocab')
            assert_that(factory.__parent__, same_instance(parent_site_manager))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            vocab = component.queryUtility(IVocabulary, name=u'test_vocab')
            assert_that(vocab.__parent__, same_instance(child_site_manager))
            assert_that(vocab.__name__, is_('test_vocab'))
            assert_that([x.value for x in iter(vocab)], contains_inanyorder('six'))
            factory = component.queryUtility(IVocabularyFactory, name=u'test_vocab')
            assert_that(factory.__parent__, same_instance(child_site_manager))

    @WithSharedApplicationMockDS(users=(u'user001', u'admin001@nextthought.com'), testapp=True, default_authenticate=False)
    def test_vocabulary_read_and_delete(self):
        admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        url = 'https://alpha.dev/dataserver2/++etc++vocabularies'
        self.testapp.get(url+'/test_vocab', status=404, extra_environ=admin_environ)

        ## register a global one.
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            vocab = component.queryUtility(IVocabulary, name=u'test_vocab')
            assert_that(vocab, same_instance(None))
            factory = component.queryUtility(IVocabularyFactory, name=u'test_vocab')
            assert_that(factory, same_instance(None))

            vocab = SimpleVocabulary([SimpleTerm(x) for x in ('a', 'b')])
            component.getGlobalSiteManager().registerUtility(vocab,
                                                             provided=IVocabulary,
                                                             name='test_vocab')
            factory = _MockVocabularyFactory()
            component.getGlobalSiteManager().registerUtility(factory,
                                                             provided=IVocabularyFactory,
                                                             name='test_vocab')

        # read
        href = url + '/test_vocab'
        result = self.testapp.get(href, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(2)}))
        assert_that([x['value'] for x in result['terms']], contains_inanyorder('a', 'b'))

        # delete
        result = self.testapp.delete(href, status=403, extra_environ=admin_environ).json_body
        assert_that(result['message'], is_('Only persistent vocabulary that created in current site can be deleted.'))

        ## create in a parent site
        parent_admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        parent_admin_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'
        result = self.testapp.post_json('https://alpha.nextthought.com/dataserver2/++etc++vocabularies',
                                        params={'name': 'test_vocab', 'terms': ['one']},
                                        status=200,
                                        extra_environ=parent_admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(1)}))

        # read
        result = self.testapp.get(href, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(1)}))

        # delete
        result = self.testapp.delete(href, status=403, extra_environ=admin_environ).json_body
        assert_that(result['message'], is_('Only persistent vocabulary that created in current site can be deleted.'))

        ## create in a child site
        result = self.testapp.post_json('https://alpha.dev/dataserver2/++etc++vocabularies',
                                        params={'name': 'test_vocab', 'terms': ['one', 'two', 'three']},
                                        status=200,
                                        extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(3)}))

        # read
        result = self.testapp.get(href, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(3)}))

        # delete
        self.testapp.delete(href, status=204, extra_environ=admin_environ)

        # read
        result = self.testapp.get(href, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(1)}))

        # delete parent vocab
        self.testapp.delete('https://alpha.nextthought.com/dataserver2/++etc++vocabularies/test_vocab',
                            status=204, extra_environ=parent_admin_environ)

        # read
        result = self.testapp.get(href, status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(2)}))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            component.getGlobalSiteManager().unregisterUtility(vocab,
                                                              provided=IVocabulary,
                                                              name='test_vocab')

            component.getGlobalSiteManager().unregisterUtility(factory,
                                                               provided=IVocabularyFactory,
                                                               name='test_vocab')
