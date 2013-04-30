#!/usr/bin/env python
"""
A decorator for various user profile-type links.
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.externalization import interfaces as ext_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.singleton import SingletonDecorator

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
LINKS = ext_interfaces.StandardExternalFields.LINKS

from nti.dataserver.links import Link

from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from .account_creation_views import REL_ACCOUNT_PROFILE_SCHEMA
_PROFILE_VIEW = '@@' + REL_ACCOUNT_PROFILE_SCHEMA
from ._util import link_belongs_to_user

from .user_activity_views import REL_USER_ACTIVITY

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IUser)
class ProfileLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, context, mapping ):
		the_links = mapping.setdefault( LINKS, [] )
		request = get_current_request()
		if request is not None and context.username == authenticated_userid(request):
			# You get your own profile schema
			link = Link( context,
						 rel=REL_ACCOUNT_PROFILE_SCHEMA,
						 elements=(_PROFILE_VIEW,) )
			link_belongs_to_user( link, context )

			the_links.append( link )
		# TODO: This is action at a distance. Refactor these to be cleaner.
		# Primary reason this are here: speed.
		link = Link( context,
					 rel=REL_USER_ACTIVITY,
					 elements=(REL_USER_ACTIVITY,))
		link_belongs_to_user( link, context )
		the_links.append( link )
