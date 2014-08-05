#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supporting authorization implementations for pyramid.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.security.interfaces import NoInteraction
from zope.security.management import checkPermission

import pyramid.authorization
from pyramid.authorization import ACLAuthorizationPolicy as _PyramidACLAuthorizationPolicy
import pyramid.security as psec
from pyramid.threadlocal import get_current_request
from pyramid.traversal import lineage as _pyramid_lineage

from nti.dataserver.authorization_acl import ACL
from nti.dataserver.authorization_acl import acl_from_aces
from nti.dataserver.authorization_acl import ace_denying_all
from nti.dataserver.authorization import ACT_UPDATE, ACT_READ, ACT_CREATE
from nti.dataserver.interfaces import ACLProxy, IAuthenticationPolicy, IAuthorizationPolicy

from nti.externalization.interfaces import StandardExternalFields

# Hope nobody is monkey patching this after we're imported

def ACLAuthorizationPolicy(_factory=_PyramidACLAuthorizationPolicy):
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
		pyramid.authorization.lineage = _lineage_that_ensures_acls

	return _factory()

def ZopeACLAuthorizationPolicy():
	"""
	A policy that brings the Zope security scheme into play, along
	with our explicit ACLs and ACL providers.

	In the initial version, we will consult Zope security scheme only
	when the ACL scheme results in a denial (this is because the Zope scheme
	uses a different set of roles and groups right now). Expect that to change
	as IAuthentication is implemented.
	"""

	class _ZopeACLAuthorizationPolicy(_PyramidACLAuthorizationPolicy):

		def permits(self, context, principals, permission):
			# Not super() for speed reasons
			permits = _PyramidACLAuthorizationPolicy.permits(self, context, principals, permission)
			# Note that we're ignoring the principals given and hence pyramid's authentication
			# policy. We assume
			# that if we have the correct interaction in place, which allows us to
			# derive the relevant principals (only a concern during impersonation)
			if not permits: # Or maybe if permits.ace == '<default deny>'?
				zope_permits = False
				# Turn IPermission objects into the strings that
				# zope expects (unless we already have a string)
				permission = getattr(permission, 'id', permission)
				try:
					zope_permits = checkPermission(permission, context)
				except NoInteraction:
					pass

				# try to maintain the debugging information from pyramid if
				# it is present
				if zope_permits:
					permits = zope_permits

			return permits

	return ACLAuthorizationPolicy(_factory=_ZopeACLAuthorizationPolicy)

_marker = object()
# These functions, particularly the lineage function, is called
# often during externalization, for many of the same objects, resulting
# in many duplicate computations of ACLs. These shouldn't be changing
# during a single request anyway. We probably want to do something long-term
# about caching the ACLs on the objects themselves, but until we do that,
# memoizing these calls on the current Request object is highly effective:
# in one test, ~2500 calls were reduced to ~477

class _Fake(object):
	pass

class _Cache(dict):
	pass

def _get_cache( obj, name ):
	cache = getattr( obj, name, None )
	if cache is None:
		cache = _Cache()
		setattr( obj, name, cache )
	return cache

def _clear_caches():
	req = get_current_request()
	if req is None:
		return

	for k, v in vars(req).items():
		if isinstance(v, _Cache):
			delattr( req, k )

import zope.testing.cleanup
zope.testing.cleanup.addCleanUp( _clear_caches )

from ZODB.POSException import POSKeyError
from nti.utils.proxy import removeAllProxies

def _lineage_that_ensures_acls(obj):
	cache = _get_cache( get_current_request() or _Fake(), '_acl_adding_lineage_cache' )
	for location in _pyramid_lineage(obj):
		try:
			# Native ACL. Run with it.
			# Note that as of 1.5a2 this can now be a callable object, which
			# would permit objects to easily manage their own ACLs using
			# our ACLProvider machinery and supporting caching on the object
			# through zope.cachedescriptors
			getattr( location, '__acl__' )
			yield location
		except AttributeError:
			# OK, can we create one?
			cache_key = id(removeAllProxies(location))
			acl = cache.get( cache_key )
			if acl is None:
				try:
					acl = ACL( location, default=_marker )
				except AttributeError:
					# Sometimes the ACL providers might fail with this;
					# especially common in test objects
					acl = _marker
				cache[cache_key] = acl

			if acl is _marker:
				# Nope. So still return the original object,
				# which pyramid will inspect and then ignore
				yield location
			else:
				# Yes we can. So do so
				yield ACLProxy( location, acl )
		except POSKeyError: # pragma: no cover
			# Yikes
			logger.warn('Cannot access ACL due to broken reference: %s', type(obj), exc_info=True)
			# It's highly likely we won't be able to get __parent__ either.
			# Check that...
			try:
				getattr( location, '__parent__')
			except (POSKeyError,AttributeError):
				break

			# Ok, we can still get __parent__, but some sub-object in our __acl__
			# raised. Now, it could be that our __acl__ was trying to
			# deny specific rights that we would otherwise inherit
			# from our parents...we can't know. We also can't know if we're
			# actually being traversed to find acls, or just to find parents...
			# for security, we return an object that denies all permissions
			fake = _Fake()
			fake.__acl__ = acl_from_aces( ace_denying_all() )
			fake.__parent__ = location.__parent__
			yield fake


def can_create(obj, request=None, skip_cache=False):
	"""
	Can the current user create over the specified object? Yes if the creator matches,
	or Yes if it is the returned object and we have permission.
	"""
	return _caching_permission_check('_acl_is_creatable_cache', ACT_CREATE, obj, request, skip_cache=skip_cache)

def is_writable(obj, request=None, skip_cache=False):
	"""
	Is the given object writable by the current user? Yes if the creator matches,
	or Yes if it is the returned object and we have permission.
	"""
	return _caching_permission_check('_acl_is_writable_cache', ACT_UPDATE, obj, request, skip_cache=skip_cache)

def is_readable(obj, request=None, skip_cache=False):
	"""
	Is the given object readable by the current user? Yes if the creator matches,
	or Yes if it is the returned object and we have permission.
	"""
	return _caching_permission_check('_acl_is_readable_cache', ACT_READ, obj, request, skip_cache=skip_cache)

def _caching_permission_check(cache_name, permission, obj, request, skip_cache=False):
	"""
	Check for the permission on the object. Assumes that the creator of the object
	has full control.
	"""
	if request is None:
		request = get_current_request()

	the_cache = _get_cache(request or _Fake(), cache_name)
	# The authentication information in use can actually change
	# during the course of a single request due to authentication (used when broadcasting events)
	# so our cache must be aware of this
	principals, authn_policy, reg = _get_effective_principals(request)
	cache_key = (id(obj), principals)

	cached_val = the_cache.get(cache_key, _marker) if not skip_cache else _marker
	if cached_val is not _marker:
		return cached_val

	# Using psec itself is "broken": It doesn't respect the current site
	# components, even if the request itself does not have a registry.
	# One way to fix this (mostly) would be to have a traversal listener
	# like the zope.site.threadSiteSubscriber that does the same thing for
	# pyramid.threadlocal, but see zope_site_tween for why that doesn't work Here we cheap out
	# and re-implement has_permission to use the desired registry.
	check_value = _has_permission( permission, obj, reg, authn_policy, principals )
	if not check_value and authn_policy is not None:
		# Try externalized objects

		# Externalized objects. The direct check and throw is faster
		# then IExternalizedObject.providedBy and an /in/
		try:
			ext_creator_name = obj[StandardExternalFields.CREATOR]
			auth_userid = authn_policy.authenticated_userid( request )

			check_value = ext_creator_name == auth_userid
		except (KeyError,AttributeError,TypeError):
			pass

	if not skip_cache:
		the_cache[cache_key] = check_value

	return check_value

def _get_effective_principals( request ):
	""" Return the principals as a tuple, plus the auth policy and registry (optimization) """
	reg = component.getSiteManager() # not pyramid.threadlocal.get_current_registry or request.registry, it ignores the site

	authn_policy = reg.queryUtility(IAuthenticationPolicy)
	if authn_policy is None:
		return (psec.Everyone,), None, reg


	principals = authn_policy.effective_principals(request) if request is not None else (psec.Everyone,)
	return tuple(principals), authn_policy, reg

def _has_permission( permission, context, reg, authn_policy, principals  ):
	"""
	Check the given permission on the given context object in the given request.

	:param request: The currently active Pyramid HTTP request object, or
		None. If not provided (and we do not look for a current request),
		then the global component registry will be used to find Authentication
		and Authorization policies, and the only principal that will be checked is
		:const:`pyramid.security.Everyone` (since there will be no identifiable
		principal from the request).

	:return: A tuple (permission, principals).
	"""
	if authn_policy is None:
		return psec.Allowed('No authentication policy in use.')

	authz_policy = reg.queryUtility(IAuthorizationPolicy)
	if authz_policy is None: # pragma: no cover
		raise ValueError('Authentication policy registered without '
						 'authorization policy') # should never happen

	return authz_policy.permits(context, principals, permission)

def has_permission( permission, context, request=None ):
	request = request or get_current_request()
	principals, authn_policy, reg = _get_effective_principals( request )
	return _has_permission( permission, context, reg, authn_policy, principals )
