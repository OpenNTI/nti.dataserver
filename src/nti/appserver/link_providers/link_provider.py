#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.appserver.interfaces import IAuthenticatedUserLinkProvider
from zope.annotation.interfaces import IAnnotations

from nti.dataserver.links import Link
from nti.dataserver.dicts import LastModifiedDict

from nti.appserver._util import link_belongs_to_user

#: The name of a view. We will construct links to it, with the actual link name
#: in the sub-path
VIEW_NAME_NAMED_LINKS = 'NamedLinks'

#: Containing a mapping
_GENERATION_LINK_KEY = __name__ + '.LinkGenerations'

@interface.implementer(IAuthenticatedUserLinkProvider)
class LinkProvider(object):

	def __init__( self, user, request, name=None, url=None, field=None, mime_type=None ):
		self.user = user
		self.request = request
		self.__name__ = name
		self.url = url
		self.mime_type = mime_type
		self.field = field

	def get_links( self ):
		link_name = self.__name__
		if self.field:
			elements = ("++fields++" + self.field,)
		else:
			# We must handle it
			elements = ("@@" + VIEW_NAME_NAMED_LINKS, link_name)
		link = Link( self.user,
					 rel=link_name,
					 elements=elements,
					 target_mime_type=self.mime_type)
		link_belongs_to_user( link, self.user )
		return (link,)

	def __repr__( self ):
		return "<%s %s %s>" % (self.__class__.__name__, self.__name__, self.url)

class ConditionalLinkProvider(LinkProvider):

	def __init__( self, *args, **kwargs ):
		self.minGeneration = kwargs.pop( 'minGeneration' )
		super(ConditionalLinkProvider,self).__init__( *args, **kwargs )

	def get_links( self ):
		link_dict = IAnnotations( self.user ).get( _GENERATION_LINK_KEY, {} )
		if link_dict.get( self.__name__, '' ) < self.minGeneration:
			# They either don't have it, or they have less than needed
			return super(ConditionalLinkProvider,self).get_links()
		# They have it and its up to date!
		return ()

	def match_generation( self ):
		link_dict = IAnnotations( self.user ).get( _GENERATION_LINK_KEY )
		if link_dict is None:
			link_dict = LastModifiedDict()
			IAnnotations( self.user )[_GENERATION_LINK_KEY] = link_dict
		link_dict[self.__name__] = self.minGeneration
