#!/usr/bin/env python

"""
A decorator for the 'account.profile' link
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
from nti.externalization import interfaces as ext_interfaces

from nti.externalization.interfaces import StandardExternalFields


from zope.location.interfaces import ILocation

from nti.dataserver.interfaces import ICreated, IUser
from nti.dataserver.links import Link
#from nti.dataserver.links_external import render_link
#from nti.dataserver.traversal import find_nearest_site
from nti.externalization.oids import to_external_ntiid_oid

from pyramid import security as psec
from pyramid.threadlocal import get_current_request

from nti.appserver.account_creation_views import REL_ACCOUNT_PROFILE
from ._util import link_belongs_to_user

LINKS = StandardExternalFields.LINKS

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(IUser) # TODO: IModeledContent?
class ProfileLinkDecorator(object):

	def __init__( self, context ): pass

	def decorateExternalMapping( self, context, mapping ):
		if context.username == psec.authenticated_userid( get_current_request() ):

			mapping.setdefault( LINKS, [] )
			link = Link( context,
						 rel=REL_ACCOUNT_PROFILE,
						 elements=('@@' + REL_ACCOUNT_PROFILE, )	)
			link_belongs_to_user( link, context )
			#if ICreated_providedBy( context ):

			mapping[LINKS].append( link )
