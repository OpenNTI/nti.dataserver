#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains views that do interesting or different things based on site policies.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.view import view_config

from zope import interface
from zope import component
from pyramid.interfaces import IView

from nti.appserver import httpexceptions as hexc

from . import site_policies

class ISiteCSSMarker(interface.Interface):
	pass

@interface.implementer(ISiteCSSMarker)
class SiteCSSMarker(object):
	pass

class ISiteStringsMarker(interface.Interface):
	pass

@interface.implementer(ISiteStringsMarker)
class SiteStringsMarker(object):
	pass

class ISiteLandingMarker(interface.Interface):
	pass

@interface.implementer(ISiteLandingMarker)
class SiteLandingMarker(object):
	pass

@interface.implementer(IView)
class LegacyResourceView(object):
	"""
	For moving off of the SiteXXXMarkers but not actually correctly
	using static views.
	"""
	def __init__( self, site, name ):
		self.site = site
		self.name = name

	def __call__( self, context, request ):
		new_path = request.path.split( '/' )[1:-1] # the path to the directory
		new_path.append( self.site )
		new_path.append( self.name )
		return hexc.HTTPSeeOther( location=request.resource_path( request.context, *new_path ) )



def _response_for_site_resource_with_marker( marker_interface, request, resource, mime_type ):
	"""
	Searches for an :class:`.IView` utility having the given resource name
	and if found, hands control over to it.

	Currently, this is invoked within a sub-space of some other
	URL tree. Specific holes are punched in proxy forwarding rules
	to send exact URL matches (down to the file) through to the routes
	that call this function. Therefore, the view that is called cannot
	assume that it can return more than one file (e.g., no siblings
	can be referenced without also mapping them somehow into the other
	URL space). This is probably a FIXME: area (to map entire directories
	through to avoid needing to change multiple URL trees).

	Static Views
	============

	To use pyramid's default static views, a site package should set
	up a directory that contains the exact paths to serve (e.g.,
	``/login/resources/css/site.css``). For example, ``views.py``
	could live beside the directory ``assets`` containing the file
	``resources/css/site.css``; then a call to
	:class:`pyramid.static.static_view` like ``static_view("assets")``
	would create a view that could be registered under the name
	``site.css``.

	Redirects and CDNs
	------------------

	Generally these resources are extremely cacheable and will not place a load
	on the dataserver. If it is desired to serve them from a CDN sometimes, however,
	a view callable can use a "static URL" request and redirect to that. In the above
	example, the view callable would return a redirect to
	``request.static_url("my.package:assets/resources/css/site.css")``, and
	the environment would have configured a static view with this path pointing
	to the CDN: ``config.add_static_view( path="my.package:assets", name="//cdn.com/assets/")``
	(usually this would be done in a pyramid ZCML file)

	Legacy Documentation
	====================
	Either redirects to a configured resource or returns an empty
	response with the give mimetype, based on the active sites. We
	should be registered as a view on a path to a CSS file, and we
	will return responses within the directory enclosing that css
	file.

	We look for a simple named utility based on the site and determine
	what to do based on its presence. We could probably simplify this
	to just redirecting unconditionally, but we might wind up getting
	lots of 404 responses which is ugly.
	"""

	view = component.queryUtility( IView, name=resource )
	if view:
		return view( request.context, request )

	# Extra legacy support...these markers are DEPRECATED
	marker, site_name = site_policies.queryUtilityInSite( marker_interface, request=request, return_site_name=True )
	if marker:
		logger.warn( "Site %s is still using legacy marker %s", site_name, marker )
		new_path = request.path.split( '/' )[1:-1] # the path to the directory
		new_path.append( site_name )
		new_path.append( resource )
		return hexc.HTTPSeeOther( location=request.resource_path( request.context, *new_path ) )

	# Nothing found
	request.response.content_type = mime_type
	request.response.text = ''
	return request.response

@view_config(route_name='logon.logon_css',
			 request_method='GET')
@view_config(route_name='webapp.site_css',
			 request_method='GET')
def site_css_view(request):
	"""
	Returns a configure site specific css or an empty response.
	We should be registered as a view on a path to a CSS file, and
	we will return responses within the directory enclosing that css file.
	"""

	return _response_for_site_resource_with_marker( ISiteCSSMarker, request, 'site.css', b'text/css' )


@view_config(route_name="logon.strings_js",
			 request_method='GET')
@view_config(route_name="webapp.strings_js",
			 request_method='GET')
def webapp_strings_view(request):
	"""
	Redirects to a site specific strings file based on the current site policy.
	"""

	# XXX: FIXME: The final part of the name of the path that matches this route
	# is 'site.js', but the resource we want to look for is actually 'strings.js',
	# This makes doing simple static redirections much harder than necessary and places
	# a lot of burden on specific implementations for sites.
	# Our hacky fix here is to adjust the PATH_INFO to reflect the desired name
	assert request.environ['PATH_INFO'].endswith( 'site.js' )
	request.environ['PATH_INFO'] = request.environ['PATH_INFO'][:-7] + 'strings.js'

	return _response_for_site_resource_with_marker( ISiteStringsMarker,
												   request,
												   'strings.js',
												   b'application/javascript')


_SITE_LANDING_COOKIE_NAME = b'nti.landing_site_name'
@view_config(route_name='landing.site_html',
			 request_method='GET')
def landing_html_view(request):
	"""
	Redirects to a site specific landing page if one exists in the current site policy.
	We do this by redirecting to last folder component of our path and setting a cookie
	for the site name.  If this site policy doesn't have a landing page we redirect without
	the cookie
	"""

	marker, site_name = site_policies.queryUtilityInSite( ISiteLandingMarker, request=request, return_site_name=True )

	#Send them a redirect to folder for this request (basically pop off the last bit)
	new_path = request.path.split( '/' )[1:-1]

	response = hexc.HTTPSeeOther( location=request.resource_path( request.context, *new_path, query=request.params ) )

	if marker:
		response.set_cookie(_SITE_LANDING_COOKIE_NAME, site_name.encode( 'utf-8' ), 600) #Live for 5 minutes.  We really just want this long enough to get through the redirect
	else:
		response.delete_cookie(_SITE_LANDING_COOKIE_NAME)

	return response
