#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines mappings from internal types to mime types

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as forum_interfaces

from nti.externalization.representation import WithRepr

from nti.mimetype.mimetype import MIME_BASE

from nti.schema.schema import EqHash
from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from . import interfaces as search_interfaces

from .constants import (POST_MIME_TYPE, NTI_CARD_MIME_TYPE, BOOK_CONTENT_MIME_TYPE,
						VIDEO_TRANSCRIPT_MIME_TYPE)

from .constants import (nticard_, content_, videotranscript_, transcript_, note_,
						highlight_, redaction_, messageinfo_, post_, forum_)


@interface.implementer(search_interfaces.ISearchTypeMetaData)
@WithRepr
@EqHash('Name', 'MimeType')
class SearchTypeMetaData(SchemaConfigured):
	createDirectFieldProperties(search_interfaces.ISearchTypeMetaData)
	
	@property
	def Type(self):
		return self.Name

	def __str__(self):
		return "%s,%s" % (self.Name, self.MimeType)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _note_metadata():
	return SearchTypeMetaData(Name=note_, MimeType=(MIME_BASE + "." + note_),
							  IsUGD=True, Order=5, Interface=nti_interfaces.INote)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _highlight_metadata():
	return SearchTypeMetaData(Name=highlight_, MimeType=(MIME_BASE + "." + highlight_),
							  IsUGD=True, Order=6, Interface=nti_interfaces.IHighlight)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _redaction_metadata():
	return SearchTypeMetaData(Name=redaction_, MimeType=(MIME_BASE + "." + redaction_),
							  IsUGD=True, Order=7, Interface=nti_interfaces.IRedaction)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _transcript_metadata():
	return SearchTypeMetaData(Name=transcript_, MimeType=(MIME_BASE + "." + transcript_),
							  IsUGD=True, Order=8, Interface=nti_interfaces.ITranscript)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _messageinfo_metadata():
	return SearchTypeMetaData(
						Name=messageinfo_, MimeType=(MIME_BASE + "." + messageinfo_),
						IsUGD=True, Order=8, Interface=chat_interfaces.IMessageInfo)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _post_metadata():
	return SearchTypeMetaData(Name=post_, MimeType=POST_MIME_TYPE,
							  IsUGD=True, Order=9, Interface=forum_interfaces.IPost)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _legacypost_metadata():
	return SearchTypeMetaData(Name=post_, MimeType=(MIME_BASE + "." + post_),
							  IsUGD=True, Order=9,
							  Interface=forum_interfaces.IPost)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _personalblogcomment_metadata():
	return SearchTypeMetaData(Name=post_,
							  MimeType=(MIME_BASE + ".forums.personalblogcomment"),
							  IsUGD=True, Order=9,
							  Interface=forum_interfaces.IPersonalBlogComment)
	
@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _generalforumcomment_metadata():
	return SearchTypeMetaData(Name=post_,
							  MimeType=(MIME_BASE + ".forums.generalforumcomment"),
							  IsUGD=True, Order=9,
							  Interface=forum_interfaces.IGeneralForumComment)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _personalblogentrypost_metadata():
	return SearchTypeMetaData(Name=post_,
							  MimeType=(MIME_BASE + ".forums.personalblogentrypost"),
							  IsUGD=True, Order=9,
							  Interface=forum_interfaces.IPersonalBlogEntryPost)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _communityheadlinepost_metadata():
	return SearchTypeMetaData(Name=post_,
							  MimeType=(MIME_BASE + ".forums.communityheadlinepost"),
							  IsUGD=True, Order=9,
							  Interface=forum_interfaces.ICommunityHeadlinePost)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _generalforum_metadata():
	return SearchTypeMetaData(Name=forum_,
							  MimeType=(MIME_BASE + ".forums.generalforum"),
							  IsUGD=True, Order=9,
							  Interface=forum_interfaces.IGeneralForum)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _communityforum_metadata():
	return SearchTypeMetaData(Name=forum_,
							  MimeType=(MIME_BASE + ".forums.communityforum"),
							  IsUGD=True, Order=9,
							  Interface=forum_interfaces.ICommunityForum)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _nticard_metadata():
	return SearchTypeMetaData(Name=nticard_, MimeType=NTI_CARD_MIME_TYPE,
							  IsUGD=False, Order=3,
							  Interface=search_interfaces.INTICardContent)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _book_metadata():
	return SearchTypeMetaData(Name=content_, MimeType=BOOK_CONTENT_MIME_TYPE,
							  IsUGD=False, Order=1,
							  Interface=search_interfaces.IBookContent)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _legacycontent_metadata():
	return SearchTypeMetaData(Name=content_, MimeType=(MIME_BASE + "." + content_),
							  IsUGD=False, Order=1,
							  Interface=search_interfaces.IBookContent)

@interface.implementer(search_interfaces.ISearchTypeMetaData)
def _videotranscript_metadata():
	return SearchTypeMetaData(Name=videotranscript_, MimeType=VIDEO_TRANSCRIPT_MIME_TYPE,
							  IsUGD=False, Order=2,
							  Interface=search_interfaces.IVideoTranscriptContent)
