#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import is_
from hamcrest import not_
from hamcrest import same_instance
from hamcrest import contains

import unittest

from zope import component

from zope.component.hooks import getSite

from zope.schema.interfaces import IVocabulary

from nti.app.vocabularyregistry.vocabulary import Vocabulary as SimpleVocabulary
from nti.app.vocabularyregistry.vocabulary import Term as SimpleTerm

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.vocabularyregistry.utils import install_named_utility

from nti.dataserver.tests import mock_dataserver

logger = __import__('logging').getLogger(__name__)


class _MockVocabularyFactory(object):

    def __call__(self, context):
        return component.queryUtility(IVocabulary, name='test_vocab')


class TestViews(ApplicationLayerTest):

    def _register_vocabulary(self, name, terms, site_manager):
        vocab = SimpleVocabulary([SimpleTerm(x) for x in terms])
        install_named_utility(vocab,
                              utility_name=name,
                              provided=IVocabulary,
                              local_site_manager=site_manager)
        assert_that(vocab.__name__, is_(name))
        assert_that(vocab.__parent__, same_instance(site_manager))
        assert_that(site_manager[name], same_instance(vocab))
        assert_that(component.queryUtility(IVocabulary, name='test_vocab'), same_instance(vocab))
        return vocab

    @WithSharedApplicationMockDS(users=(u'user001', u'admin001@nextthought.com'), testapp=True, default_authenticate=False)
    def testVocabularyUpdateView(self):
        # Register an vocabulary in alpha.nextthought.com
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            parent_site_manager = getSite().getSiteManager()
            self._register_vocabulary(name='test_vocab',
                                      terms=('a', 'b'),
                                      site_manager=parent_site_manager)

        # update in parent site
        admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'

        self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.dev/++etc++site/test_vocab',
                              params={'terms': []},
                              status=404, extra_environ=admin_environ)

        result = self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                                       params={'terms': ['zzz', 'xx', 'yyy']},
                                       status=200, extra_environ=admin_environ).json_body

        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(3)}))
        assert_that([x['value'] for x in result['terms']], contains('zzz', 'xx', 'yyy'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__name__, is_('test_vocab'))
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            assert_that(parent_site_manager['test_vocab'], same_instance(vocab))
            assert_that([x.value for x in iter(vocab)], contains('zzz', 'xx', 'yyy'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            assert_that([x.value for x in iter(vocab)], contains('zzz', 'xx', 'yyy'))

        # update in child site
        admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'

        self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.dev/++etc++site/test_vocab',
                              params={'terms': []},
                              status=404, extra_environ=admin_environ)

        result = self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                                       params={'terms': ['ok', 'yes']},
                                       status=200, extra_environ=admin_environ).json_body

        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(2)}))
        assert_that([x['value'] for x in result['terms']], contains('ok', 'yes'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            assert_that(getSite().getSiteManager(), same_instance(parent_site_manager))
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__name__, is_('test_vocab'))
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            assert_that(parent_site_manager['test_vocab'], same_instance(vocab))
            assert_that([x.value for x in iter(vocab)], contains('ok', 'yes'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            assert_that(getSite().getSiteManager(), not_(parent_site_manager))
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            assert_that(parent_site_manager['test_vocab'], same_instance(vocab))
            assert_that([x.value for x in iter(vocab)], contains('ok', 'yes'))

        # Register an vocabulary in alpha.dev
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            child_site_manager = getSite().getSiteManager()
            assert_that(parent_site_manager, not_(child_site_manager))
            self._register_vocabulary(name='test_vocab',
                                      terms=('e', 'c'),
                                      site_manager=child_site_manager)

        # update in child site
        admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'

        result = self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.dev/++etc++site/test_vocab',
                                       params={'terms': ['hello']},
                                       status=200, extra_environ=admin_environ).json_body
        assert_that(result, has_entries({'name': 'test_vocab', 'terms': has_length(1)}))
        assert_that([x['value'] for x in result['terms']], contains('hello'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__name__, is_('test_vocab'))
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            assert_that(parent_site_manager['test_vocab'], same_instance(vocab))
            assert_that([x.value for x in iter(vocab)], contains('ok', 'yes'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__parent__, same_instance(child_site_manager))
            assert_that(child_site_manager['test_vocab'], same_instance(vocab))
            assert_that([x.value for x in iter(vocab)], contains('hello'))

        self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                              params={'terms': [' world ']},
                              status=200, extra_environ=admin_environ)

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__name__, is_('test_vocab'))
            assert_that(vocab.__parent__, same_instance(parent_site_manager))
            assert_that(parent_site_manager['test_vocab'], same_instance(vocab))
            assert_that([x.value for x in iter(vocab)], contains('world'))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(vocab.__parent__, same_instance(child_site_manager))
            assert_that(child_site_manager['test_vocab'], same_instance(vocab))
            assert_that([x.value for x in iter(vocab)], contains('hello'))

        # duplicated terms
        result = self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                              params={'terms': ['world', 'hello', 'world']},
                              status=422, extra_environ=admin_environ).json_body
        assert_that(result['message'], is_("term values must be unique: u'world'"))

        result = self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                              params={'terms': None},
                              status=422, extra_environ=admin_environ).json_body
        assert_that(result['message'], is_("terms should be an array of strings."))

        result = self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                              params={'terms': ['abc', '    ']},
                              status=422, extra_environ=admin_environ).json_body
        assert_that(result['message'], is_("'    ' is not non-empty string."))

        result = self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                              params={'terms': ['abc', True]},
                              status=422, extra_environ=admin_environ).json_body
        assert_that(result['message'], is_("'True' is not non-empty string."))

        # 403
        user_environ = self._make_extra_environ(username='user001')
        user_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        self.testapp.put_json('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                              params={'terms': ['world', 'hello', 'world']},
                              status=403, extra_environ=user_environ)

    @unittest.skip("Disable the deletion view for now.")
    @WithSharedApplicationMockDS(users=(u'user001', u'admin001@nextthought.com'), testapp=True, default_authenticate=False)
    def testVocabularyDeleteView(self):
        # NT admin can delete any vocabularies from any sites.
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            parent_site_manager = getSite().getSiteManager()
            vocab = self._register_vocabulary(name='test_vocab',
                                              terms=('a', 'b'),
                                              site_manager=parent_site_manager)
            queried_vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(queried_vocab, same_instance(vocab))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            child_site_manager = getSite().getSiteManager()
            child_vocab = self._register_vocabulary(name='test_vocab',
                                              terms=('z',),
                                              site_manager=child_site_manager)
            queried_child_vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(queried_child_vocab, same_instance(child_vocab))
            assert_that(queried_child_vocab, not_(queried_vocab))

        # 401
        anonymous_environ = self._make_extra_environ(username=None)
        anonymous_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        self.testapp.delete('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                            status=401,
                            extra_environ=anonymous_environ)

        # 403
        user_environ = self._make_extra_environ(username='user001')
        user_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        self.testapp.delete('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                            status=403,
                            extra_environ=user_environ)
        self.testapp.delete('/dataserver2/++etc++hostsites/alpha.dev/++etc++site/test_vocab',
                            status=403,
                            extra_environ=user_environ)

        # 200
        admin_environ = self._make_extra_environ(username='admin001@nextthought.com')
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'

        # remove
        self.testapp.delete('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                            status=204,
                            extra_environ=admin_environ)
        self.testapp.delete('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                            status=404,
                            extra_environ=admin_environ)
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            queried_vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(queried_vocab, is_(None))
            assert_that(parent_site_manager, not_(has_key('test_vocab')))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            queried_vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(queried_vocab.__parent__, same_instance(child_site_manager))
            assert_that(child_site_manager, has_key('test_vocab'))

        # remove
        self.testapp.delete('/dataserver2/++etc++hostsites/alpha.dev/++etc++site/test_vocab',
                            status=204,
                            extra_environ=admin_environ)
        self.testapp.delete('/dataserver2/++etc++hostsites/alpha.dev/++etc++site/test_vocab',
                            status=404,
                            extra_environ=admin_environ)
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            queried_vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(queried_vocab, is_(None))
            assert_that(child_site_manager, not_(has_key('test_vocab')))

    @WithSharedApplicationMockDS(users=(u'user001', u'admin001@nextthought.com'), testapp=True, default_authenticate=False)
    def testVocabularyGetView(self):
        # Authenticated users can read any vocabulary from any other sites.
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            vocab = self._register_vocabulary(name='test_vocab',
                                              terms=('a', 'b'),
                                              site_manager=getSite().getSiteManager())
            queried_vocab = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(queried_vocab, same_instance(vocab))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            vocab1 = self._register_vocabulary(name='test_vocab',
                                              terms=('z', 'x', 'y'),
                                              site_manager=getSite().getSiteManager())
            queried_vocab1 = component.queryUtility(IVocabulary, name='test_vocab')
            assert_that(queried_vocab1, same_instance(vocab1))
            assert_that(queried_vocab1, not_(queried_vocab))

        environs = []
        for username in ('user001', 'admin001@nextthought.com'):
            for hostname in ('http://alpha.nextthought.com', 'http://alpha.dev', 'http://demo.dev'):
                environ = self._make_extra_environ(username=username)
                environ['HTTP_ORIGIN'] = hostname
                environs.append(environ)

        assert_that(environs, has_length(6))
        for environ in environs:
            result = self.testapp.get('/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/test_vocab',
                                      status=200,
                                      extra_environ=environ).json_body
            assert_that(result, has_entries({'Class': 'Vocabulary',
                                             'name': 'test_vocab',
                                             'terms': has_length(2)}))
            assert_that(result['terms'][0], has_entries({'Class': 'Term',
                                                         'value': 'a'}))
            assert_that(result['terms'][1], has_entries({'Class': 'Term',
                                                         'value': 'b'}))

        for environ in environs:
            result = self.testapp.get('/dataserver2/++etc++hostsites/alpha.dev/++etc++site/test_vocab',
                                      status=200,
                                      extra_environ=environ).json_body
            assert_that(result, has_entries({'Class': 'Vocabulary',
                                             'name': 'test_vocab',
                                             'terms': has_length(3)}))
            assert_that(result['terms'][0], has_entries({'Class': 'Term',
                                                         'value': 'z'}))
            assert_that(result['terms'][1], has_entries({'Class': 'Term',
                                                         'value': 'x'}))
            assert_that(result['terms'][2], has_entries({'Class': 'Term',
                                                         'value': 'y'}))

        anonymous_environ = self._make_extra_environ(username=None)
        anonymous_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        self.testapp.get('/dataserver2/++etc++hostsites/alpha.dev/++etc++site/test_vocab',
                         status=401,
                         extra_environ=anonymous_environ)
        self.testapp.get('/dataserver2/++etc++hostsites/demo.dev/++etc++site/test_vocab',
                         status=404,
                         extra_environ=anonymous_environ)
