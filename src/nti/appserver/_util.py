#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common utility classes and functions for the appserver.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson as json
import collections

from pyramid.security import authenticated_userid, remember
from pyramid.threadlocal import get_current_request

from zope import interface
from zope.event import notify
from zope.proxy.decorator import SpecificationDecoratorBase
from zope.location.interfaces import ILocation

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization import oids as ext_oids

from nti.dataserver import links
from nti.dataserver import users

from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces
from nti.dataserver.interfaces import ICreated

class AbstractTwoStateViewLinkDecorator(object):
	"""
	A decorator which checks the state of a predicate of two functions (the object and username)
	and adds one of two links depending on the value of the predicate. The links
	are to views on the original object having the same name as the ``rel`` attribute of the generated
	link.

	Instances define the following attributes:

	.. py:attribute:: predicate

		The function of two paramaters (object and username) to call

	.. py:attribute:: false_view

		The name of the view to use when the predicate is false.

	.. py:attribute:: true_view

		The name of the view to use when the predicate is true.

	If the resolved view name (i.e., one of ``false_view`` or ``true_view``) is ``None``,
	then no link will be added.

	.. note:: This may cause the returned objects to be user-specific,
		which may screw with caching.
	"""

	false_view = None
	true_view = None
	predicate = None

	def __init__( self, ctx ):
		pass

	def decorateExternalMapping( self, context, mapping ):
		current_username = authenticated_userid( get_current_request() )
		if not current_username:
			return

		# We only do this for parented objects. Otherwise, we won't
		# be able to render the links. A non-parented object is usually
		# a weakref to an object that has been left around
		# in somebody's stream
		if not context.__parent__:
			return

		predicate_passed = self.predicate( context, current_username )
		# We're assuming that because you can see it, you can (un)like it.
		# this matches the views
		rel = self.true_view if predicate_passed else self.false_view
		if rel is None: # Disabled in this case
			return

		# Use the NTIID rather than the 'physical' path because the 'physical'
		# path may not quite be traversable at this point
		target_ntiid = ext_oids.to_external_ntiid_oid( context )
		if target_ntiid is None:
			logger.warn( "Failed to get ntiid; not adding link %s for %s", rel, context )
			return

		link = links.Link( target_ntiid, rel=rel, elements=('@@' + rel,) )
		interface.alsoProvides( link, ILocation )
		link.__name__ = ''
		link.__parent__ = context

		_links = mapping.setdefault( StandardExternalFields.LINKS, [] )
		_links.append( link )

@interface.implementer(app_interfaces.IUncacheableInResponse)
class _UncacheableInResponseProxy(SpecificationDecoratorBase):
	"""
	A proxy that itself implements UncacheableInResponse. Note
	that we must extend SpecificationDecoratorBase if we're going
	to be implementing things, otherwise if we try to do `interface.alsoProvides`
	on a plain ProxyBase object it falls through to the original object,
	which defeats the point.
	"""

	# when/if these are pickled, they are pickled as their original type,
	# not the proxy.



def uncached_in_response( context ):
	"""
	Cause the `context` value to not be cacheable when used in a pyramid
	response.

	Because the context object is likely to be persistent, this uses
	a proxy and causes the proxy to also implement :class:`nti.appserver.interfaces.IUncacheableInResponse`
	"""
	return context if app_interfaces.IUncacheableInResponse.providedBy(context) else _UncacheableInResponseProxy( context )

def logon_userid_with_request( userid, request, response=None ):
	"""
	Mark that the user has logged in. This is done by notifying a :class:`nti.appserver.interfaces.IUserLogonEvent`.

	:param basestring userid: The account name that should be logged in.
	:param request: Pyramid request that is active and responsible for the login.
	:param response: If given, then the response will be given the headers
		to remember the logon.
	:raise ValueError: If the userid does not belong to a valid user.
	"""

	# Send the logon event
	dataserver = request.registry.getUtility(nti_interfaces.IDataserver)
	user = users.User.get_user( username=userid, dataserver=dataserver )
	if not user:
		raise ValueError( "No user found for %s" % userid )

	logon_user_with_request( user, request, response=response )

def logon_user_with_request( user, request, response=None ):
	"""
	Mark that the user has logged in. This is done by notifying a :class:`nti.appserver.interfaces.IUserLogonEvent`.

	:param user: The user object that should be logged in.
	:param request: Pyramid request that is active and responsible for the login.
	:param response: If given, then the response will be given the headers
		to remember the logon. Otherwise, the request's response will.
	:raise ValueError: If the user is None.
	"""

	# Send the logon event
	if not nti_interfaces.IUser.providedBy( user ):
		raise ValueError( "No valid user given" )

	notify( app_interfaces.UserLogonEvent( user, request ) )

	response = response or getattr( request, 'response' )
	if response:
		response.headers.extend( remember( request, user.username.encode('utf-8') ) )
		response.set_cookie( b'username', user.username.encode( 'utf-8' ) ) # the web app likes this

def dump_stacks():
	"""
	Request information about the running threads of the current process.

	:return: A sequence of text lines detailing the stacks of running
		threads and greenlets. (One greenlet will duplicate one thread,
		the current thread and greenlet.)
	"""
	dump = []

	# threads
	import threading # Late import this stuff because it may get monkey-patched
	import sys
	import gc
	import traceback
	from greenlet import greenlet

	threads = {th.ident: th.name for th in threading.enumerate()}

	for thread, frame in sys._current_frames().items():
		dump.append('Thread 0x%x (%s)\n' % (thread, threads.get(thread)))
		dump.append(''.join(traceback.format_stack(frame)))
		dump.append('\n')

	# greenlets


	# if greenlet is present, let's dump each greenlet stack
	# Use the gc module to inspect all objects to find the greenlets
	# since there isn't a global registry
	for ob in gc.get_objects():
		if not isinstance(ob, greenlet):
			continue
		if not ob:
			continue   # not running anymore or not started
		dump.append('Greenlet %s\n' % ob)
		dump.append(''.join(traceback.format_stack(ob.gr_frame)))
		dump.append('\n')

	return dump

def dump_stacks_view(request):
	body = '\n'.join(dump_stacks())
	print( body )
	request.response.text = body
	request.response.content_type = b'text/plain'
	return request.response


def raise_json_error( request,
					  factory,
					  v,
					  tb ):
	"""
	Attempts to raise an error during processing of a pyramid request.
	We expect the client to specify that they want JSON errors.

	:param v: The detail message. Can be a string or a dictionary. A dictionary
		may contain the keys `field`, `message` and `code`.
	:param factory: The factory (class) to produce an HTTP exception.
	:param tb: The traceback from `sys.exc_info`.
	"""
	#logger.exception( "Failed to create user; returning expected error" )
	mts = (b'application/json', b'text/plain')
	accept_type = b'application/json'
	if getattr(request, 'accept', None):
		accept_type = request.accept.best_match( mts )

	if isinstance( v, collections.Mapping ) and v.get( 'field' ) == 'username':
		# Our internal schema field is username, but that maps to Username on the outside
		v['field'] = 'Username'

	if accept_type == b'application/json':
		try:
			v = json.dumps( v )
		except TypeError:
			v = str(v)
	else:
		v = str(v)

	result = factory()
	result.body = v
	result.content_type = accept_type
	raise result, None, tb

def link_belongs_to_user( link, user ):
	link.__parent__ = user
	link.__name__ = ''
	interface.alsoProvides( link, ILocation )
	try:
		link.creator = user
		interface.alsoProvides( link, ICreated )
	except AttributeError:
		pass
	return link
