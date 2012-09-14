#!/usr/bin/env python

"""
A decorator for the 'edit' link
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
from nti.externalization import interfaces as ext_interfaces

from nti.externalization.interfaces import StandardExternalFields

from nti.appserver.pyramid_authorization import is_writable

import persistent.interfaces

from zope.location.interfaces import ILocation

from nti.dataserver.interfaces import ICreated, ILink
from nti.dataserver.links import Link
from nti.dataserver.links_external import render_link
from nti.dataserver.traversal import find_nearest_site
from nti.externalization.oids import to_external_ntiid_oid


ILink_providedBy = ILink.providedBy
ICreated_providedBy = ICreated.providedBy

LINKS = StandardExternalFields.LINKS

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class EditLinkDecorator(object):
	"""
	Adds the ``edit`` link relationship to persistent objects (because we have to be able
	to generat a URL and we need the OID) that are writable by the current user.
	"""

	def __init__( self, context ):
		pass

	def decorateExternalMapping( self, context, mapping ):

		if not getattr( context, '_p_jar' ):
			return
		# preflight, make sure there is no edit link already
		# is_writable is relatively expensive
		for l in mapping.get(LINKS,()):
			try:
				if l.rel == 'edit':
					return
			except AttributeError:
				pass

		if is_writable( context ):
			# TODO: This is weird, assuming knowledge about the URL structure here
			# Should probably use request ILocationInfo to traverse back up to the ISite
			__traceback_info__ = context, mapping
			try:
				# Some objects are not in the traversal tree. Specifically,
				# chatserver.IMeeting (which is IModeledContent and IPersistent)
				# Our options are to either catch that here, or introduce an
				# opt-in interface that everything that wants 'edit' implements
				nearest_site = find_nearest_site( context )
			except TypeError:
				nearest_site = None

			if nearest_site is None:
				logger.debug( "Not providing edit links for %s, could not find site", type(context) )
				return

			mapping.setdefault( LINKS, [] )
			link = Link( to_external_ntiid_oid( context ), rel='edit' )
			link.__parent__ = context
			link.__name__ = ''
			interface.alsoProvides( link, ILocation )
			try:
				link.creator = context.creator
				interface.alsoProvides( link, ICreated )
			except AttributeError:
				pass
			#if ICreated_providedBy( context ):

			mapping[LINKS].append( link )

			# For cases that we can, make edit and the toplevel href be the same.
			# this improves caching
			mapping['href'] = render_link( link, nearest_site=nearest_site )['href']
