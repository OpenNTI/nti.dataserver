#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.location.interfaces import ILocation

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.dataserver import links
from nti.dataserver.links_external import render_link
from nti.dataserver.traversal import find_nearest_site

from ..interfaces import IContentUnitInfo

@interface.implementer(IExternalMappingDecorator)
@component.adapter(IContentUnitInfo) # TODO: IModeledContent?
class ContentUnitInfoHrefDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, context, mapping ):
		if 'href' in mapping:
			return

		try:
			# Some objects are not in the traversal tree. Specifically,
			# chatserver.IMeeting (which is IModeledContent and IPersistent)
			# Our options are to either catch that here, or introduce an
			# opt-in interface that everything that wants 'edit' implements
			nearest_site = find_nearest_site( context )
		except TypeError:
			nearest_site = None

		if nearest_site is None:
			logger.debug("Not providing href links for %s, could not find site", 
						 type(context) )
			return

		link = links.Link( nearest_site, elements=('Objects', context.ntiid) )
		# Nearest site may be IRoot, which has no __parent__
		link.__parent__ = getattr(nearest_site, '__parent__', None) 
		link.__name__ = ''
		interface.alsoProvides( link, ILocation )
	
		mapping['href'] = render_link( link, nearest_site=nearest_site )['href']
