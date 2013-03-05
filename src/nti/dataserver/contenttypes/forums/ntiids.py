#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NTIID resolvers.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from . import interfaces as frm_interfaces
from nti.ntiids import interfaces as nid_interfaces

from nti.ntiids import ntiids
from nti.dataserver.ntiids import AbstractUserBasedResolver


@interface.implementer( nid_interfaces.INTIIDResolver )
class _BlogResolver(AbstractUserBasedResolver):
	"Resolves the one blog that belongs to a user, if one does exist."

	def _resolve( self, ntiid, user ):
		return frm_interfaces.IPersonalBlog( user, None )

@interface.implementer( nid_interfaces.INTIIDResolver )
class _BlogEntryResolver(AbstractUserBasedResolver):
	"""Resolves a single blog entry within a user."""

	def _resolve( self, ntiid, user ):
		blog_name = ntiids.get_specific( ntiid )
		blog = frm_interfaces.IPersonalBlog( user, {} )
		# because of this, __name__ of the entry must be NTIID safe
		return blog.get( blog_name )
