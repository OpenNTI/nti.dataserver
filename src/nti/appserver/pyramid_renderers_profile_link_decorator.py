#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A decorator for various user profile-type links.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from pyramid.threadlocal import get_current_request

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

from nti.dataserver import interfaces as nti_interfaces

from nti.links.links import Link

from ._util import link_belongs_to_user
from .user_activity_views import REL_USER_ACTIVITY
from .account_creation_views import REL_ACCOUNT_PROFILE_SCHEMA

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
LINKS = ext_interfaces.StandardExternalFields.LINKS

_PROFILE_VIEW = '@@' + REL_ACCOUNT_PROFILE_SCHEMA

@component.adapter(nti_interfaces.IUser)
@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class ProfileLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		request = get_current_request()
		the_links = mapping.setdefault(LINKS, [])
		if request is not None and context.username == request.authenticated_userid:
			# You get your own profile schema
			link = Link(context,
					 	rel=REL_ACCOUNT_PROFILE_SCHEMA,
						elements=(_PROFILE_VIEW,))
			link_belongs_to_user(link, context)
			the_links.append(link)

		# TODO: This is action at a distance. Refactor these to be cleaner.
		# Primary reason this are here: speed.
		link = Link(context,
					rel=REL_USER_ACTIVITY,
					elements=(REL_USER_ACTIVITY,))
		link_belongs_to_user(link, context)
		the_links.append(link)
