#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import isodate
from datetime import datetime

from zope import component
from .interfaces import IBulkEmailProcessLoop

from nti.dataserver import authorization as nauth

from nti.mailer.interfaces import ITemplatedMailer

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

class _Status(object):
	"""
	For viewing status information, as passed
	to the renderer.
	"""

	def __init__( self, process ):
		self.process = process

	def __getattr__( self, name ):
		try:
			return getattr( self.process, name )
		except AttributeError:
			return getattr( self.process.metadata, name )

	def _time(self, name):
		startTime = getattr( self.metadata, name )
		if startTime:
			return isodate.datetime_isoformat( datetime.fromtimestamp(startTime) )

	def startTimeISO(self):
		return self._time('startTime')
	def endTimeISO(self):
		return self._time('endTime')

	def processRunning(self):
		# We use the existence of the lock 'file' as a proxy
		# to determine if the process loop is running somewhere
		return self.redis.exists( self.names.lock_name )

@view_defaults( route_name='objects.generic.traversal',
				name='bulk_email_admin',
				permission=nauth.ACT_MODERATE,
			  )
class _BulkEmailView(object):

	_greenlets = []

	def __init__( self, request ):
		self.request = request
		self._name = None

	def _find_process(self):
		process = component.queryAdapter(self.request, IBulkEmailProcessLoop, name=self._name)
		if process is None:
			# Testing
			process = getattr(self, '_test_make_process', lambda: None)()

		if process is None:
			raise hexc.HTTPNotFound()
		process.__name__ = self._name
		return process

	def _preflight(self):
		if not self.request.subpath:
			raise hexc.HTTPNotFound()

		self._name = self.request.subpath[0]
		process = self._find_process()
		template_name = getattr( process.delegate, 'template_name', None ) or self.request.subpath[0]

		if not component.getUtility(ITemplatedMailer).do_html_text_templates_exist(template_name,
																				   text_template_extension=getattr(process.delegate,
																												   'text_template_extension',
																												   '.txt')):
			raise hexc.HTTPNotFound("No such templates found") # XXX: Why are we doing this?

		process.template_name = template_name
		process.request = self.request
		return process

	@view_config(request_method='GET',
				 renderer='templates/bulk_email_admin.pt')
	def get(self):
		process = self._preflight()

		status = _Status( process )
		self.request.context = status
		# Use a dict to override the context argument that pyramid
		# directly inserts
		return {'context': status}

	@view_config(request_method='POST',
				 renderer='templates/bulk_email_admin.pt')
	def post(self):
		process = self._preflight()
		request = self.request
		if 'subFormTable.buttons.resume' in self.request.POST:
			process.metadata.status = 'Resumed'
			process.metadata.save()
			greenlet = request.nti_gevent_spawn( run=process.process_loop )
			# ICK. Must save this somewhere so it doesn't get
			# GC'd. Where?
			_BulkEmailView._greenlets.append( greenlet )
		elif 'subFormTable.buttons.initialize' in self.request.POST:
			# need to collect and then spawn the process
			process.initialize()
		elif 'subFormTable.buttons.start' in self.request.POST:
			# need to collect and then spawn the process
			process.initialize()
			greenlet = request.nti_gevent_spawn( run=process.process_loop )
			# ICK. Must save this somewhere so it doesn't get
			# GC'd. Where?
			_BulkEmailView._greenlets.append( greenlet )
		elif 'subFormTable.buttons.reset' in self.request.POST:
			process.reset_process()

		# Redisplay the page with a get request to avoid the "re-send this POST?" problem
		get_path = self.request.path  + (('?' + self.request.query_string) if self.request.query_string else '')
		return hexc.HTTPFound(location=get_path)

	@classmethod
	def _cleanup(cls):
		del cls._greenlets[:]

import zope.testing.cleanup
zope.testing.cleanup.addCleanUp( _BulkEmailView._cleanup )
