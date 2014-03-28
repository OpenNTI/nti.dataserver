#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides a tween for integrating Pyramid with the Zope security
model of a thread-local interaction. Rather than monkey-patching
zope.security.management or something to pull data from pyramid's
request on demand, this tween simply sets up and tears down
an interaction.

This tween must be run in a transaction and with the root site set
(so below :mod:`.zope_site_tween`).

.. note:: :mod:`zope.security` uses a thread-local variable for this,
   so when gevent is involved the order of importing or patching
   matters greatly.

Request Modifications
=====================

No modifications are exposed on the request object. Instead, see
:mod:`zope.security.management` or :class:`zope.security.interfaces.IInteractionManagement`.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# In pure zope, it is zope.publisher that sets up the interaction.
# The IPublisherRequest is-a IParticipation. Rather than make
# the pyramid request do that, lets keep things simple and separate.

from zope import interface
from zope import component

from zope.security.interfaces import IPrincipal
from zope.security.interfaces import IParticipation

from zope.security.management import newInteraction, endInteraction

from nti.dataserver.interfaces import IDataserver
from nti.dataserver import users

@interface.implementer(IParticipation)
class _Participation(object):

	__slots__ = 'interaction', 'principal'

	def __init__( self, principal ):
		self.interaction = None
		self.principal = principal

class _interaction_tween(object):

	__slots__ = ('handler',)

	def __init__( self, handler ):
		self.handler = handler

	def __call__( self, request ):
		uid = request.authenticated_userid
		if uid:
			dataserver = component.getUtility( IDataserver )
			# We must have a user at this point...
			user = users.User.get_user(uid, dataserver=dataserver)
			# ...and all users must be IPrincipal-capable
			principal = IPrincipal(user)
			# newInteraction takes a list of participations.
			# it's important that the first one be the main IPrincipal,
			# but if we use this for more than preferences we probably
			# need to include roles (effective principals?)
			newInteraction(_Participation(principal))

		try:
			return self.handler(request)
		finally:
			# Whether or not we started one, it is always
			# safe to end it
			endInteraction()

def security_interaction_tween_factory(handler, registry):
	return _interaction_tween( handler )
