#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import contains_inanyorder

from nti.testing.matchers import validly_provides

import unittest

from repoze.who.interfaces import IRequestClassifier

from nti.app.authentication.who_classifiers import APP_CLASSES
from nti.app.authentication.who_classifiers import CLASS_BROWSER_APP

from nti.app.authentication.who_classifiers import application_request_classifier as _nti_request_classifier


class TestClassifier(unittest.TestCase):

    def test_delete_is_not_dav(self):
        assert_that(_nti_request_classifier,
                    validly_provides(IRequestClassifier))

        # By default requests get classified as dav
        environ = {}
        environ['REQUEST_METHOD'] = 'DELETE'

        assert_that(_nti_request_classifier(environ), is_('dav'))

        # But dav, like browser get's reclassified
        environ['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        assert_that(_nti_request_classifier(environ),
                    is_(CLASS_BROWSER_APP))

    def test_request_classifier(self):

        assert_that(_nti_request_classifier,
                    validly_provides(IRequestClassifier))

        # The default
        environ = {}
        environ['REQUEST_METHOD'] = 'GET'

        assert_that(_nti_request_classifier(environ), is_('browser'))

        # XHR
        environ['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        assert_that(_nti_request_classifier(environ),
                    is_(CLASS_BROWSER_APP))
        # case-insensitive
        environ['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'.upper()
        assert_that(_nti_request_classifier(environ),
                    is_(CLASS_BROWSER_APP))

        del environ['HTTP_X_REQUESTED_WITH']

        environ['HTTP_REFERER'] = 'http://foo'

        # A referrer alone isn't enough
        assert_that(_nti_request_classifier(environ), is_('browser'))

        # Add  a user agent
        environ['HTTP_USER_AGENT'] = 'Mozilla'
        __traceback_info__ = environ
        assert_that(_nti_request_classifier(environ), is_(CLASS_BROWSER_APP))

        # But a default accept changes back to browser
        environ['HTTP_ACCEPT'] = '*/*'
        assert_that(_nti_request_classifier(environ), is_('browser'))

        environ['HTTP_ACCEPT'] = 'text/plain'
        assert_that(_nti_request_classifier(environ), is_(CLASS_BROWSER_APP))

        environ['HTTP_ACCEPT'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        assert_that(_nti_request_classifier(environ), is_('browser'))

        # We've seen badly encoded (?) headers in the wild; we shouldn't blow up
        # This one was clearly from a mobile phone in Brazil (dating from 2011;
        # note how old the Androad version is)
        environ['HTTP_USER_AGENT'] = ('Mozilla/5.0 (Linux; U; Android 2.3.4; pt-BR; KG-P970h Build/GRJ22) '
                                      'AppleWebKit/533.1 (KHTML, like Gecko) '
                                      'Vers\xe3o/4.0 Mobile Safari/533.1')
        assert_that(_nti_request_classifier(environ), is_('browser'))

        # Temporary hack for old iPad apps
        environ['HTTP_USER_AGENT'] = "NTIFoundation DataLoader NextThought/1.0.2/34053 (x86_64; 7.0.3)"
        assert_that(_nti_request_classifier(environ), is_(CLASS_BROWSER_APP))

        environ['HTTP_USER_AGENT'] = "NextThought/1.0.2 CFNetwork/672.0.8 Darwin/13.0.0"
        assert_that(_nti_request_classifier(environ), is_(CLASS_BROWSER_APP))

        del environ['HTTP_REFERER']
        environ['HTTP_USER_AGENT'] = "NTIFoundation DataLoader NextThought/1.0.2/34053 (x86_64; 7.0.3)"
        assert_that(_nti_request_classifier(environ), is_(CLASS_BROWSER_APP))

        environ['HTTP_USER_AGENT'] = "NextThought/1.0.2 CFNetwork/672.0.8 Darwin/13.0.0"
        assert_that(_nti_request_classifier(environ), is_(CLASS_BROWSER_APP))

    def test_app_classes(self):
        # We have a well known set of app classes
        assert_that(APP_CLASSES, contains_inanyorder(CLASS_BROWSER_APP,))
