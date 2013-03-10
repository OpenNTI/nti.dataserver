#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for creating Atom and RSS feeds from UGD streams. Atom is highly recommended.

A typical URL will look something like ``/dataserver2/users/$USER/Pages($NTIID)/RecursiveStream/feed.atom.``
Your newsreader will need to support HTTP Basic Auth; on the Mac I highly
recommend NetNewsWire.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"
import logging
logger = logging.getLogger(__name__)

import feedgenerator
import datetime

from pyramid.view import view_config

from zope import interface
from zope import component

from zope.dublincore import interfaces as dc_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.contentfragments import interfaces as frg_interfaces

from nti.appserver import httpexceptions as hexc
from nti.appserver.ugd_query_views import _RecursiveUGDStreamView

from nti.dataserver import authorization as nauth

from nti.externalization.externalization import to_external_representation
from nti.externalization.oids import to_external_ntiid_oid

import html5lib
from html5lib import treebuilders
#from html5lib.filters._base import Filter as FilterBase

import lxml.etree

class _BetterDateAtom1Feed(feedgenerator.Atom1Feed):
	"""
	Provides the ``published`` element for atom feeds; if this
	is missing and only ``updated`` is present (the default in the super class)
	some readers will fail to present a valid date.
	"""
	def add_item_elements(self, handler, item):
		super(_BetterDateAtom1Feed,self).add_item_elements( handler, item )
		if item.get('published') is not None:
			handler.addQuickElement(u"published", feedgenerator.rfc3339_date(item['published']).decode('utf-8'))


class AbstractFeedView(object):
	"""
	Primary view for producing Atom and RSS feeds. Accepts the same filtering
	parameters as :class:`nti.appserver.ugd_query_views._RecursiveUGDStreamView`
	so you can control what types of actions you see in the feed as well as the
	length of the feed.

	"""

	def __init__( self, request ):
		self.request = request

	# TODO: We could probably do this with named adapters
	_data_callable_factory = None

	def _object_and_creator( self, data_item ):
		raise NotImplementedError()

	def _feed_title( self ):
		raise NotImplementedError()

	def __call__( self ):
		request = self.request
		response = request.response

		stream_view = self._data_callable_factory( request )
		ext_dict = stream_view() # May raise HTTPNotFound
		response.last_modified = ext_dict['Last Modified']

		# TODO: This borrows alot from the REST renderers
		if response.last_modified is not None and request.if_modified_since:
			# Since we know a modification date, respect If-Modified-Since. The spec
			# says to only do this on a 200 response
			# This is a pretty poor time to do it, after we've done all this work
			if response.last_modified <= request.if_modified_since:
				not_mod = hexc.HTTPNotModified()
				not_mod.last_modified = response.last_modified
				not_mod.cache_control = 'must-revalidate'
				raise not_mod


		feed_factory = feedgenerator.Rss201rev2Feed if request.view_name == 'feed.rss' else _BetterDateAtom1Feed

		feed = feed_factory(
			title=self._feed_title(),
			link=request.application_url,
			feed_url=request.path_url,
			description='',
			language='en' )

		for data_item in ext_dict['Items']:
			data_object, data_creator, data_title, data_categories = self._object_and_creator( data_item )

			renderer = IFeedRenderer( data_object, None )
			descr = renderer.render() if renderer else ''

			creator_profile = user_interfaces.IUserProfile( data_creator )
			feed.add_item(
				title=data_title,
				link=request.application_url, # TODO: Not right
				description=descr,
				author_email=getattr( creator_profile, 'email', None ),
				author_name=creator_profile.realname or creator_profile.alias or unicode(data_creator),
				pubdate=dc_interfaces.IDCTimes( data_item ).created,
				unique_id=to_external_ntiid_oid(data_object),
				categories=data_categories,
				# extras. If we don't provide a 'published' date
				updated=dc_interfaces.IDCTimes( data_item ).modified,
				published=dc_interfaces.IDCTimes( data_item ).created,
				)


		feed_string = feed.writeString( 'utf-8' )
		response.content_type = feed.mime_type.encode( 'utf-8' )
		response.body = feed_string

		return response


@view_config( route_name='user.pages.odata.traversal.feeds',
			  context='nti.appserver.interfaces.IPageContainerResource',
			  name='feed.rss',
			  permission=nauth.ACT_READ, request_method='GET',
			  http_cache=datetime.timedelta(hours=1))
@view_config( route_name='user.pages.odata.traversal.feeds',
			  context='nti.appserver.interfaces.IPageContainerResource',
			  name='feed.atom',
			  permission=nauth.ACT_READ, request_method='GET',
			  http_cache=datetime.timedelta(hours=1))
class UGDFeedView(AbstractFeedView):
	_data_callable_factory = _RecursiveUGDStreamView

	def _object_and_creator( self, change ):
		creator_profile = user_interfaces.IUserProfile( change.creator )
		title = "%s %s a %s" % (creator_profile.realname or creator_profile.alias or change.creator, change.type.lower(), change.object.__class__.__name__)
		return change.object, change.creator, title, (change.type,)

	def _feed_title( self ):
		return self.request.context.ntiid # TODO: Better title

class IFeedRenderer(interface.Interface):

	def render():
		"""
		Render to an HTML string the context object.
		"""

@interface.implementer(IFeedRenderer)
@component.adapter(nti_interfaces.INote)
class NoteFeedRenderer(object):
	"""
	Renderers notes in HTML for feeds. Does what it can with canvas objects,
	which is to include their URL.

	.. note:: This is similar to :class:`nti.appserver._table_utils.NoteBodyColumn`.

	"""
	def __init__( self, context ):
		self.context = context

	def render(self):
		parts = []
		for part in self.context.body:
			if nti_interfaces.ICanvas.providedBy( part ):
				for shape in part.shapeList:
					url = getattr( shape, 'url', None )
					if url:
						ext_url = shape.toExternalObject()['url']
						if nti_interfaces.ILink.providedBy( ext_url ):
							ext_url = to_external_representation( ext_url, 'json' )
						part = "<img src=%s />" % ext_url
					else:
						part = None
			elif frg_interfaces.IHTMLContentFragment.providedBy( part ):
				parser = html5lib.HTMLParser( tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False )
				doc = parser.parse( part )
				body = doc.find('body')
				if body:
					part = lxml.etree.tostring( body, method='html', encoding=unicode )
					part = part[6:-7] # strip the enclosing body tag
				else:
					part = None
			else:
				part = frg_interfaces.IPlainTextContentFragment( part, None ) or unicode(part)

			if part:
				parts.append( part )
		return '<br />'.join( parts )

@interface.implementer(IFeedRenderer)
@component.adapter(nti_interfaces.ISelectedRange)
class SelectedRangeFeedRenderer(object):
	"""
	For highlights and the like.
	"""

	def __init__( self, context ):
		self.context = context

	def render(self):
		return self.context.selectedText

@interface.implementer(IFeedRenderer)
@component.adapter(nti_interfaces.IEntity)
class EntityFeedRenderer(object):
	"""
	For circled users.
	"""

	def __init__( self, context ):
		self.context = context

	def render(self):
		return self.context.username
