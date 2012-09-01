#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains views that do interesting or different things based on site policies.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.appserver import interfaces as app_interfaces
from nti.appserver import site_policies
from nti.appserver import httpexceptions as hexc

from pyramid.view import view_config


class ISiteCSSMarker(interface.Interface):
	pass

@interface.implementer(ISiteCSSMarker)
class SiteCSSMarker(object):
	pass

@view_config(route_name='logon.logon_css',
			 request_method='GET')
def logon_site_css_view(request):
	"""
	Either redirects to a configured site css, or returns an empty CSS, based
	on the active sites. We should be registered as a view on a path to a CSS file, and
	we will return responses within the directory enclosing that css file.

	We look for a simple named utility based on the site and determine what to
	do based on its presence. We could probably simplify this to just redirecting
	unconditionally, but we might wind up getting lots of 404 responses which is ugly.
	"""

	for site_name in site_policies.get_possible_site_names():
		marker = component.queryUtility( ISiteCSSMarker, name=site_name )

		if marker:
			new_path = request.path.split( '/' )[1:-1] # the path to the directory
			new_path.append( site_name )
			new_path.append( 'site.css' )
			return hexc.HTTPSeeOther( location=request.resource_path( request.context, *new_path ) )

	# Nothing found
	request.response.content_type = 'text/css'
	request.response.text = ''
	return request.response
