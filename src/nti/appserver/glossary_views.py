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
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import datetime
from cStringIO import StringIO

from zope import component
from zope.lifecycleevent.interfaces import IObjectCreatedEvent

from pyramid import httpexceptions as hexc
from pyramid.view import view_config, view_defaults

import nti.appserver.interfaces as app_interfaces

from nti.contentlibrary import interfaces as lib_interfaces
from nti.contentlibrary.eclipse import MAIN_CSV_CONTENT_GLOSSARY_FILENAME

from nti.dataserver import authorization as nauth

import nti.dictserver as dictserver
import nti.dictserver.interfaces as dict_interfaces
from nti.dictserver.storage import TrivialExcelCSVDataStorage

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
	@view_config( context=app_interfaces.INewPageContainerResource )
	def __call__(self):
		request = self.request
		term = request.subpath[0]

		ntiid = request.context.ntiid

		# Currently, we only support merging in content-specific glossary values
		library = request.registry.queryUtility( lib_interfaces.IContentPackageLibrary )
		if library:
			path = library.pathToNTIID( ntiid ) or ()
		else:
			path = ()

		# Collect all the dictionaries, from most specific to global
		dictionaries = []
		for unit in path:
			unit_dict = request.registry.queryUtility( dict_interfaces.IDictionaryTermDataStorage, name=unit.ntiid )
			dictionaries.append( unit_dict )
		dictionaries.append( request.registry.queryUtility( dict_interfaces.IDictionaryTermDataStorage ) )

		info = term
		for dictionary in dictionaries:
			if dictionary is not None:
				info = dictserver.lookup( info, dictionary=dictionary )

		if info is term:
			# No dictionaries at all were found
			raise hexc.HTTPNotFound()

		# Save a unicode string into the body
		request.response.text = info.toXMLString(encoding=None)
		request.response.content_type = b'text/xml'
		# Let the web layer encode to utf-8 (the default for XML)
		request.response.charset = b'utf-8'
		request.response.status_int = 200

		return request.response

@component.adapter(lib_interfaces.IContentPackage,IObjectCreatedEvent)
def add_main_glossary_from_new_content( title, event ):
	glossary_source = title.read_contents_of_sibling_entry( MAIN_CSV_CONTENT_GLOSSARY_FILENAME )
	if glossary_source:
		logger.info( "Adding content-glossary from %s at %s", title, title.ntiid )
		csv_dict = TrivialExcelCSVDataStorage( StringIO( glossary_source ) )
		component.provideUtility( csv_dict, name=title.ntiid )
