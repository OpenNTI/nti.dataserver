#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supporting authorization implementations for pyramid.


$Id$
"""
from __future__ import print_function, unicode_literals

logger = __import__( 'logging' ).getLogger(__name__)

from nti.dataserver.authorization import ACT_UPDATE
from nti.dataserver.authorization_acl import ACL
from nti.dataserver.interfaces import ACLProxy

from nti.externalization.interfaces import StandardExternalFields, IExternalizedObject

import pyramid.authorization
import pyramid.security as psec
from pyramid.traversal import lineage as _pyramid_lineage
from pyramid.threadlocal import get_current_request
# Hope nobody is monkey patching this after we're imported

def ACLAuthorizationPolicy():
	"""
	An :class:`pyramid.interfaces.IAuthorizationPolicy` that processes
	ACLs in exactly the same way as :class:`pyramid.authorization.ACLAuthorizationPolicy`,
	with the exception that it uses :func:`nti.dataserver.authorization_acl.ACL` (and
	all the supporting adapter machinery) to get an object's ACL.

	.. note:: Using this object has the side-effect of causing use of a "raw"
		:class:`pyramid.authorization.ACLAuthorizationPolicy` to also start respecting
		this machinery. This will only have any visible impact in the case that an object did
		not already declare its own ACL.
	"""

	# The behaviour of the ACLAuthorizationPolicy is exactly what we want,
	# except that we want to use our function to get ACLs. The class doesn't
	# allow for this, hardcoding access to object.__acl__ twice. The simplest way
	# to get what we want is to patch the 'lineage' function it uses to return proxy
	# objects if there is no native ACL, but we can generate one

	if pyramid.authorization.lineage is _pyramid_lineage:
		# patch it
		logger.debug( "patching pyramid.authorization to use ACL providers" )
		pyramid.authorization.lineage = _acl_adding_lineage

	return pyramid.authorization.ACLAuthorizationPolicy()

_marker = object()
def _acl_adding_lineage(obj):
	for location in _pyramid_lineage(obj):
		try:
			# Native ACL. Run with it.
			location.__acl__
			yield location
		except AttributeError:
			# OK, can we create one?
			try:
				acl = ACL( location, default=_marker )
			except AttributeError:
				# Sometimes the ACL providers might fail with this;
				# especially common in test objects
				acl = _marker

			if acl is _marker:
				# Nope. So still return the original object,
				# which pyramid will inspect and then ignore
				yield location
			else:
				# Yes we can. So do so
				yield ACLProxy( location, acl )

def is_writable(obj, request=None):
	"""
	Is the given object writable by the current user? Yes if the creator matches,
	or Yes if it is the returned object and we have permission.
	"""
	if request is None:
		request = get_current_request()

	return psec.has_permission( ACT_UPDATE, obj, request ) \
	  or (IExternalizedObject.providedBy( obj )
		  and StandardExternalFields.CREATOR in obj
		  and obj[StandardExternalFields.CREATOR] == psec.authenticated_userid( request ) )
