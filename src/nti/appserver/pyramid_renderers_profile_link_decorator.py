#!/usr/bin/env python

"""
A decorator for the 'account.profile' link
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component


from nti.externalization import interfaces as ext_interfaces
from nti.dataserver import interfaces as nti_interfaces

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
LINKS = ext_interfaces.StandardExternalFields.LINKS


from nti.dataserver.links import Link

from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from .account_creation_views import REL_ACCOUNT_PROFILE
_PROFILE_VIEW = '@@' + REL_ACCOUNT_PROFILE
from ._util import link_belongs_to_user

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IUser) # TODO: IModeledContent?
class ProfileLinkDecorator(object):

	def __init__( self, context ):
		pass

	def decorateExternalMapping( self, context, mapping ):
		if context.username == authenticated_userid( get_current_request() ):

			the_links = mapping.setdefault( LINKS, [] )
			link = Link( context,
						 rel=REL_ACCOUNT_PROFILE,
						 elements=(_PROFILE_VIEW,) )
			link_belongs_to_user( link, context )

			the_links.append( link )
