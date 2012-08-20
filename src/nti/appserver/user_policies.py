#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Policies based on the user. See also :mod:`nti.appserver.site_policies` for
site-based policies.
For content censoring policies based on the user, see :mod:`nti.appserver.censor_policies`.

This module is curently where preventing sharing for coppa kids is implemented.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.dataserver import interfaces as nti_interfaces

from zope.lifecycleevent import IObjectCreatedEvent
from zope.lifecycleevent import IObjectModifiedEvent

from . import httpexceptions as hexc

@component.adapter(nti_interfaces.IModeledContent, IObjectCreatedEvent)
def dispatch_content_created_to_user_policies( content, event ):
	component.handle( content, content.creator, event )

from pyramid import security as psec
from pyramid.threadlocal import get_current_request
from nti.dataserver import users

@component.adapter(nti_interfaces.IModeledContent, IObjectModifiedEvent)
def dispatch_content_edited_to_user_policies( content, event ):
	editor = users.User.get_user( psec.authenticated_userid( get_current_request() ) )
	component.handle( content, editor, event )

@component.adapter(nti_interfaces.IModeledContent, nti_interfaces.ICoppaUserWithoutAgreement, IObjectCreatedEvent)
def veto_sharing_for_unsigned_coppa_create( content, creator, event ):
	if content.sharingTargets:
		raise hexc.HTTPForbidden( "Cannot share objects" )

@component.adapter(nti_interfaces.IModeledContent, nti_interfaces.ICoppaUserWithoutAgreement, IObjectModifiedEvent)
def veto_sharing_for_unsigned_coppa_edit( content, editor, event ):
	if content.sharingTargets:
		raise hexc.HTTPForbidden( "Cannot share objects" )
