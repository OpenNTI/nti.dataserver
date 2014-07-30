#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common utility classes and functions for the appserver.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.security import remember

from zope import interface
from zope.event import notify
from zope.location.interfaces import ILocation

from nti.appserver.interfaces import UserLogonEvent

from nti.dataserver import users
from nti.dataserver.interfaces import ICreated
from nti.dataserver import interfaces as nti_interfaces

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.renderers.caching",
	"nti.app.renderers.caching",
	# This was a class, just in case there are pickles this should stay
	# here even after all clients are updated
	"_UncacheableInResponseProxy",
	"uncached_in_response"
	)

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

	notify(UserLogonEvent(user, request))

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

from ZODB.interfaces import IDatabase
from zope import component

def dump_database_cache(gc=False):
	"""
	Request information about the various ZODB database caches
	and returns a sequence of text lines describing them.

	:keyword gc: If set to True, then each database will be
		asked to minimize its cache.
	"""

	db = component.queryUtility(IDatabase)
	if db is None:
		return ["No database"]

	databases = db.databases or {'': db}
	lines = []
	for name, value in databases.items():
		lines.append( "Database\tCacheSize" )
		lines.append( "%s\t%s" % (name, value.cacheSize()) )

		lines.append("\tConnections")
		for row in value.cacheDetailSize():
			lines.append( "\t\t%s" % row )

		lines.append("\tTypes")
		for kind, count in sorted(value.cacheDetail(),key=lambda x: x[1]):
			lines.append( '\t\t%s\t%s' % (kind, count))

		if gc:
			value.cacheMinimize()

	return lines


zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.externalization.internalization",
	"nti.app.externalization.internalization",
	"create_modeled_content_object",
	"class_name_from_content_type",
	"read_body_as_external_object",
	"update_object_from_external_object")

zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.externalization.error",
	"nti.app.externalization.error",
	"raise_json_error")

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
