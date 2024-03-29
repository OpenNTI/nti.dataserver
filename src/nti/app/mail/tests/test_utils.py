#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import assert_that

from zope import component
from zope import interface

from zope.security.interfaces import IPrincipal

from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.users import User as _DSUser

from nti.mailer.interfaces import IMailerPolicy
from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import IPrincipalEmailValidation

from nti.app.testing.layers  import AppLayerTest

from nti.coremetadata.interfaces import IDeactivatedUser


class TestUtils(AppLayerTest):

	def test_bounced_emails(self):

		@interface.implementer(IPrincipal, IEmailAddressable, IUserProfile)
		class User(object):
			username = 'the_user'
			id = 'the_user'
			email = 'thomas.stockdale@nextthought.com'

		user = User()

		validator = IPrincipalEmailValidation(user, None)
		assert_that(validator, not_none())

		user.email_verified = None
		assert_that(validator.is_valid_email(), is_(True))

		interface.alsoProvides(user, IDeactivatedUser)
		assert_that(validator.is_valid_email(), is_(False))
		interface.noLongerProvides(user, IDeactivatedUser)

		user.email_verified = True
		assert_that(validator.is_valid_email(), is_(True))

		user.email_verified = False
		assert_that(validator.is_valid_email(), is_(False))

		ds_user = _DSUser(username=u'bounced_username')
		validator = IPrincipalEmailValidation(ds_user, None)
		assert_that(validator, not_none())

	def test_policy(self):
		policy = component.queryUtility(IMailerPolicy)
		assert_that(policy, not_none())
		assert_that(policy.get_default_sender(), none())
		assert_that(policy.get_signer_secret(), none())




