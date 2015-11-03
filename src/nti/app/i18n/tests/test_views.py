#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from zope import interface

from hamcrest import is_
from nti.app.testing.application_webtest import ApplicationLayerTest
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import calling
from hamcrest import raises
from zope.event import notify


from nti.dataserver.interfaces import IUser
import fudge

from pyramid.request import Request
from pyramid.events import ContextFound
def adjust(request):
	notify(ContextFound(request))

from ..views import StringsLocalizer

from pyramid.httpexceptions import HTTPNotFound


class TestApplicationViews(ApplicationLayerTest):

	request = None
	view = None

	def setUp(self):
		self.request = Request.blank('/')
		self.request.environ[b'HTTP_ACCEPT_LANGUAGE'] = b'ru'
		self.view = StringsLocalizer(self.request)
		self.view._DOMAIN = 'nti.dataserver'

	def test_no_domain_found(self):
		self.view._DOMAIN = 'this domain should never exist'
		assert_that( calling(self.view),
					 raises(HTTPNotFound))

	@fudge.patch('nti.app.i18n.subscribers.get_remote_user',
				 'nti.app.i18n.adapters.get_remote_user')
	def test_adjust_remote_user_default(self, fake_get1, fake_get2):
		@interface.implementer(IUser)
		class User(object):
			pass

		fake_get1.is_callable().returns(User())
		fake_get2.is_callable().returns(User())


		adjust(self.request)
		# The accept header rules
		res = self.view()

		assert_that( res,
					 has_property( 'location',
								   'http://localhost/app/resources/locales/ru/LC_MESSAGES/nti.dataserver.js'))
