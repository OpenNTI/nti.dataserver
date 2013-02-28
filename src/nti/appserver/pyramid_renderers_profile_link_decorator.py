#!/usr/bin/env python
"""
A decorator for various user profile-type links.
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.annotation.interfaces import IAnnotations

from nti.externalization import interfaces as ext_interfaces
from nti.dataserver import interfaces as nti_interfaces

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
LINKS = ext_interfaces.StandardExternalFields.LINKS


from nti.dataserver.links import Link

from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from .account_creation_views import REL_ACCOUNT_PROFILE_SCHEMA
_PROFILE_VIEW = '@@' + REL_ACCOUNT_PROFILE_SCHEMA
from ._util import link_belongs_to_user

from .pyramid_authorization import is_readable

from .user_activity_views import REL_USER_ACTIVITY

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IUser)
class ProfileLinkDecorator(object):

	def __init__( self, context ):
		pass

	def decorateExternalMapping( self, context, mapping ):
		the_links = mapping.setdefault( LINKS, [] )
		request = get_current_request()
		if context.username == authenticated_userid( request ):
			# You get your own profile schema
			link = Link( context,
						 rel=REL_ACCOUNT_PROFILE_SCHEMA,
						 elements=(_PROFILE_VIEW,) )
			link_belongs_to_user( link, context )

			the_links.append( link )
		# TODO: This is action at a distance. Refactor these to be cleaner.
		# Primary reason they are here: speed.
		# notice we DO NOT adapt; it must already exist
		blog = context.containers.getContainer( 'Blog' ) # see forum_views
		if blog and is_readable( blog, request ):
			link = Link( context,
						 rel='Blog',
						 elements=('Blog',) )
			link_belongs_to_user( link, context )
			the_links.append( link )

		link = Link( context,
					 rel=REL_USER_ACTIVITY,
					 elements=(REL_USER_ACTIVITY,))
		link_belongs_to_user( link, context )
		the_links.append( link )
