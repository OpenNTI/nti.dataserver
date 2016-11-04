#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Application authentication related interfaces.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

class IUserTokenCreator(interface.Interface):
	"""
	Something that can create logon tokens for the
	user.
	"""
	# Or maybe this should be an adapter on the request?

	def getTokenForUserId( userid ):
		"""
		Given a logon id for a user, return a long-lasting
		token. If this cannot be done, return None.
		"""

class IIdentifiedUserTokenCreator(IUserTokenCreator):
	"""
	Something that generates tokens that are self-identifiable
	(carry around the userid they are for and optionally
	other information).
	"""

	userid_key = interface.Attribute("The key in the identity dictionary representing the userid.")

	def getIdentityFromToken(token):
		"""
		Given a token previously produced by this object,
		return a dictionary representing the information
		extracted from it. The dictionary will have a key
		named by :attr:`userid_key` that represents the userid.

		If this cannot be done, returns None.
		"""

class IUserTokenChecker(interface.Interface):
	"""
	Something that can determine if the token is valid
	for the user.
	"""

	def tokenIsValidForUserid( token, userid ):
		"""
		Given a userid and a token, determine if the token
		is valid for the user.
		"""

class IIdentifiedUserTokenChecker(IUserTokenChecker):

	def identityIsValid( identity ):
		"""
		Check if an identity previously returned
		from :meth:`getIdentityFromToken` is actually
		valid for the claimed user. This should return the claimed
		userid, or None.
		"""

class IUserTokenAuthenticator(IUserTokenCreator,
							  IUserTokenChecker):
	"""
	Something that can create and consume user tokens.
	"""

class IIdentifiedUserTokenAuthenticator(IIdentifiedUserTokenCreator,
										IUserTokenAuthenticator):
	pass


class ILogonWhitelist(interface.Interface):
	"""
	A container of usernames that are allowed to login (be authenticated).
	"""

	def __contains__(username):
		"Return true if the username can login."

@interface.implementer(ILogonWhitelist)
class EveryoneLogonWhitelist(object):
	"""
	Everyone is allowed to logon.
	"""

	def __contains__(self, username):
		return True
