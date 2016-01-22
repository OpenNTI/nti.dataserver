#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integrations with :mod:`zope.pluggableauth``

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.authentication.interfaces import ILoginPassword

from zope.pluggableauth.factories import PrincipalInfo
from zope.pluggableauth.interfaces import IAuthenticatorPlugin

from nti.app.authentication.interfaces import ILogonWhitelist

from nti.dataserver.users import User

@interface.implementer(IAuthenticatorPlugin)
class DataserverUsersAuthenticatorPlugin(object):
	"""
	Globally authenticates principals.
	"""

	def authenticateCredentials(self, credentials):
		"""
		Authenticate the user based on whitelist and presented
		credentials.

		The credentials are either a dictionary containing "login" and
		\"password\", or an instance of :class:`.ILoginPassword`
		"""
		login = None
		password = None
		if ILoginPassword.providedBy(credentials):
			login = credentials.getLogin()
			password = credentials.getPassword()
		else:
			login = credentials.get('login')
			password = credentials.get('password')

		whitelist = component.getUtility(ILogonWhitelist)
		if login not in whitelist:
			return None

		user = User.get_user(login)
		if user is None or user.password is None:
			return None

		if user.password.checkPassword(password):
			return self.principalInfo(login)

	def principalInfo(self, pid):
		user = User.get_user(pid)
		if user is not None:
			# TODO: Better title and description
			return PrincipalInfo(pid, pid, pid, pid)
