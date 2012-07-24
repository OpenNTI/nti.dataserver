#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implements the views for presenting glossary entries to a user.

Looking up a glossary/dictionary entry involves three parameters:

* The active user. The active user may have a personal glossary. In addition,
  the classes that are currently active for the user may have glossaries (e.g.,
  terms the teacher has defined specially).
* The active content (and its position in the tree.) A particular piece of content
  may add a glossary, and any entry it has for a term will be added to the entries found
  for glossaries defined by parent units, all the way up to the global (Root) dictionary.
* And of course the term itself.

These three parameters represent too many degrees to capture in a simple traversal
URL. That is, there is no single correct "canonical" location for a dictionary/glossary
entry. Therefore, uniformity, practicality, and caching considerations dictate
a URL structure that matches the one used for other content-specific (page) data:
:samp:`.../users/{user}/Pages({ntiid})/Glossary/{term}`. In this structure, ``Glossary`` is the
view name, and ``term`` is the subpath.

On the surface, having the username in the URL hurts caching, if there are primarily (only)
shared glossary entries. However, if many entries come from the (permissioned)
content, class or personal glossaries, the clarity is a net win (since it's one less thing that
would have to be crammed into a ``Vary`` header, and we can probably set longer expiration
times).


$Id$
"""
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

import datetime

from pyramid.view import view_config, view_defaults
from pyramid import httpexceptions as hexc

import nti.appserver.interfaces as app_interfaces
import nti.dictserver as dictserver
from nti.dataserver import authorization as nauth

@view_defaults(name='Glossary',
			   route_name='objects.generic.traversal',
			   request_method='GET',
			   permission=nauth.ACT_READ,
			   http_cache=datetime.timedelta(days=1) )
class GlossaryView(object):
	"""
	Primary reading glossary view.
	"""
	def __init__( self, request ):
		self.request = request

	@view_config( context=app_interfaces.IPageContainerResource )
	@view_config( context=app_interfaces.INewContainerResource )
	def __call__(self):
		# Obviously none of the configuration
		# and traversal and merging is here yet.
		# This is a straightforward
		request = self.request
		term = request.subpath[0]


		info = dictserver.WordInfo( term )
		try:
			dictserver.lookup( info )
		except (KeyError,ValueError): # pragma: no cover
			# Bad/missing JSON dictionary data.
			# We probably shouldn't ever get this far
			logger.exception( "Bad or missing dictionary data" )
			return hexc.HTTPNotFound()

		# Save a unicode string into the body
		request.response.text = info.toXMLString(encoding=None)
		request.response.content_type = b'text/xml'
		# Let the web layer encode to utf-8 (the default for XML)
		request.response.charset = b'utf-8'
		request.response.status_int = 200

		return request.response
