#!/usr/bin/env python
"""
Defines traversal views and resources for the dataserver.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__( 'logging' ).getLogger( __name__ )

from zope import component
from zope.location.location import LocationProxy

from pyramid.view import view_defaults

from nti.appserver import httpexceptions as hexc
from nti.app.base.abstract_views import AbstractView
from nti.appserver import interfaces as app_interfaces
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

class _ServiceGetView(AbstractAuthenticatedView):

	def __call__( self ):
		# JAM: We should make this a multi-adapter on the request
		# so that the request can be threaded down through workspaces,
		# collections, etc.
		service = app_interfaces.IService(self.remoteUser)
		#service.__parent__ = self.request.context
		return service

@view_defaults(route_name='objects.generic.traversal',
			   permission=nauth.ACT_READ,
			   renderer='rest',
			   request_method='GET')
class _GenericGetView(AbstractView):

	def __call__( self ):
		# TODO: We sometimes want to change the interface that we return
		# We're doing this to turn a dataserver IContainer (which externalizes poorly)
		# to an ICollection (which externalizes nicely.) How to make this
		# configurable/generic?
		# For right now, we're looking for an adapter registered with the name of the
		# last component we traversed, and then falling back to the default

		# TODO: Assuming the result that we get is some sort of container,
		# then we're leaving the renderer to insert next/prev first/last related
		# links and handle paging. Is that right?
		# NOTE: We'll take either one of the wrapper classes defined
		# in this module, or the object itself
		resource = getattr( self.request.context, 'resource', self.request.context )

		if nti_interfaces.IDeletedObjectPlaceholder.providedBy(resource):
			raise hexc.HTTPNotFound()

		result = component.queryAdapter( resource,
										 app_interfaces.ICollection,
										 name=self.request.traversed[-1] )
		if not result:
			result = component.queryAdapter( resource,
											 app_interfaces.ICollection,
											 default=resource )
		if hasattr( result, '__parent__' ):
			# FIXME: Choosing which parent to set is also borked up.
			# Some context objects (resources) are at the same conceptual level
			# as the actual request.context, some are /beneath/ that level??
			# If we have a link all the way back up to the root, we're good?
			# TODO: This can probably mostly go away now?
			if result is resource:
				# Must be careful not to modify the persistent object
				result = LocationProxy( result, getattr( result, '__parent__', None), getattr( result, '__name__', None ) )
			if getattr( resource, '__parent__', None ) is not None:
				result.__parent__ = resource.__parent__
				# FIXME: Another hack at getting the right parent relationship in.
				# The actual parent relationship is to the Provider object,
				# but it has no way back to the root resource. This hack is deliberately
				# kept very specific for now.
				if self.request.traversed[-1] == 'Classes' and self.request.traversed[0] == 'providers':
					result.__parent__ = self.request.context.__parent__
				elif self.request.traversed[-1] == 'Pages' and self.request.traversed[0] == 'users':
					result.__parent__ = self.request.context.__parent__
			elif resource is not self.request.context and hasattr( self.request.context, '__parent__' ):
				result.__parent__ = self.request.context.__parent__
		return result

GenericGetView = _GenericGetView

class _EmptyContainerGetView(AbstractView):

	def __call__( self ):
		raise hexc.HTTPNotFound( self.request.context.ntiid )

def _method_not_allowed(request):
	raise hexc.HTTPMethodNotAllowed()
