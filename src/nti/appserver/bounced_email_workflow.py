#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tools and views for dealing with bounced emails. Bounce notifications go
to an SQS queue where they are processed in batch by running the command
provided in this module. Permanent failures are found and correlated
to user accounts (with substantial logging). The user profile of these
accounts is updated to remove the email, since it is invalid (and continuing to get
bounces for it can make Amazon SES very angry), and links are added to the
user for the application to notice at the next logon time:

.. py:data:: REL_INVALID_EMAIL

	The link relationship type (``state-bounced-email``) that
	indicates we know that the email recorded for this user is bad and
	has received permanent bounces. The user must be asked to enter a
	new one and update the profile. Send an HTTP DELETE to this link
	when you are done updating the profile to remove the flag.

.. py:data:: REL_INVALID_CONTACT_EMAIL

	The link relationship type (``state-bounced-contact-email``) that
	indicates that a contact email (aka parent email) recorded for
	this (under 13) user has received permanent bounces. The child
	must be asked to enter a new contact_email and update the profile.
	When the profile is updated, a new consent email will be
	generated. Send an HTTP DELETE to this link with you are done
	updating the profile to remove the flag.

.. note:: It might be possible for the server to detect the update events and
  automatically clear the link. I'm not sure.

.. note:: The only thing the client can do with these links is DELETE them.
  Would it be useful for them to serve as PUT aliases to update the profile?
  That just seems to complicate the clint which already 'knows' how to update
  the profile (but it could be handy from the command line).

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

REL_INVALID_EMAIL = 'state-bounced-email'
REL_INVALID_CONTACT_EMAIL = 'state-bounced-contact-email'

from pyramid.view import view_config

from nti.appserver.user_link_provider import AbstractUserLinkDeleteView

class BouncedEmailDeleteView(AbstractUserLinkDeleteView):

	LINK_NAME = REL_INVALID_EMAIL

	@view_config(name=REL_INVALID_EMAIL)
	def __call__( self ):
		return AbstractUserLinkDeleteView.__call__( self )


class BouncedContactEmailDeleteView(AbstractUserLinkDeleteView):

	LINK_NAME = REL_INVALID_CONTACT_EMAIL

	@view_config(name=REL_INVALID_CONTACT_EMAIL)
	def __call__( self ):
		return AbstractUserLinkDeleteView.__call__( self )
