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

from zope.dublincore import interfaces as dc_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.appserver import httpexceptions as hexc
from nti.appserver._table_utils import NoteBodyColumn
from nti.appserver.pyramid_renderers import compress_body
from nti.appserver.ugd_query_views import _RecursiveUGDStreamView

from nti.dataserver import authorization as nauth
from nti.externalization.oids import to_external_ntiid_oid


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
def feed_view( request ):
	response = request.response

	stream_view = _RecursiveUGDStreamView(request)
	ext_dict = stream_view()
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


	feed_factory = feedgenerator.Rss201rev2Feed if request.view_name == 'feed.rss' else feedgenerator.Atom1Feed

	feed = feed_factory(
		title=request.context.ntiid, # TODO: Better title
		link=request.application_url,
		feed_url=request.path_url,
		description='',
		language='en' )

	# TODO: adapters
	note_description_maker = NoteBodyColumn(None,None,None).renderCell

	for change in ext_dict['Items']:
		descr = ''
		if nti_interfaces.INote.providedBy( change.object ):
			descr = note_description_maker( change.object )
		elif nti_interfaces.IHighlight.providedBy( change.object ):
			descr = change.object.selectedText

		creator_profile = user_interfaces.IUserProfile( change.creator )
		feed.add_item(
			title="%s %s a %s" % (creator_profile.realname or creator_profile.alias or change.creator, change.type.lower(), change.object.__class__.__name__),
			link=request.application_url, # TODO: Not right
			description=descr,
			author_email=getattr( creator_profile, 'email', None ),
			author_name=getattr( creator_profile, 'realname', None ), # TODO: Alias or something
			pubdate=dc_interfaces.IDCTimes( change ).created,
			unique_id=to_external_ntiid_oid(change.object),
			categories=(change.type,) )


	response.content_type = feed.mime_type
	response.body = compress_body( request, response, feed.writeString('utf-8'), False )

	return response
