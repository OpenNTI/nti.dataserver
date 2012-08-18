#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common utility classes and functions for the appserver.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

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

class AbstractTwoStateViewLinkDecorator(object):
	"""
	A decorator which checks the state of a predicate of two functions (the object and username)
	and adds one of two links depending on the value of the predicate. The links
	are to views having the same name as the ``rel`` attribute of the generated
	link.

	Instances define the following attributes:

	.. py:attribute:: predicate

		The function of two paramaters (object and username) to call

	.. py:attribute:: false_view

		The name of the view to use when the predicate is false.

	.. py:attribute:: true_view

		The name of the view to use when the predicate is true.

	.. note:: This may cause the returned objects to be user-specific,
		which may screw with caching.
	"""

	false_view = None
	true_view = None
	predicate = None

	def __init__( self, ctx ):
		pass

	def decorateExternalMapping( self, context, mapping ):
		current_user = authenticated_userid( get_current_request() )
		if not current_user:
			return

		# We only do this for parented objects. Otherwise, we won't
		# be able to render the links. A non-parented object is usually
		# a weakref to an object that has been left around
		# in somebody's stream
		if not context.__parent__:
			return

		i_like = self.predicate( context, current_user )
		_links = mapping.setdefault( StandardExternalFields.LINKS, [] )
		# We're assuming that because you can see it, you can (un)like it.
		# this matches the views
		rel = self.true_view if i_like else self.false_view
		# Use the NTIID rather than the 'physical' path because the 'physical'
		# path may not quite be traversable at this point
		link = links.Link( ext_oids.to_external_ntiid_oid( context ), rel=rel, elements=('@@' + rel,) )
		interface.alsoProvides( link, ILocation )
		link.__name__ = ''
		link.__parent__ = context
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

	notify( app_interfaces.UserLogonEvent( user, request ) )

	if response:
		response.headers.extend( remember( request, user.username.encode('utf-8') ) )

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
	request.response.content_type = 'text/plain'
	return request.response
