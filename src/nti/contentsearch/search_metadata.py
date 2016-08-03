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

from nti.chatserver.interfaces import IMessageInfo

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForum
from nti.dataserver.contenttypes.forums.interfaces import ICommunityForum
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForumComment
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogComment
from nti.dataserver.contenttypes.forums.interfaces import ICommunityHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IHighlight
from nti.dataserver.interfaces import IRedaction
from nti.dataserver.interfaces import ITranscript

from nti.externalization.representation import WithRepr

from nti.mimetype.mimetype import MIME_BASE

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from .interfaces import IBookContent
from .interfaces import INTICardContent
from .interfaces import ISearchTypeMetaData
from .interfaces import IAudioTranscriptContent
from .interfaces import IVideoTranscriptContent

from .constants import VIDEO_TRANSCRIPT_MIME_TYPE, AUDIO_TRANSCRIPT_MIME_TYPE
from .constants import POST_MIME_TYPE, NTI_CARD_MIME_TYPE, BOOK_CONTENT_MIME_TYPE

from .constants import content_, nticard_
from .constants import audiotranscript_, videotranscript_, transcript_
from .constants import note_, highlight_, redaction_, messageinfo_, post_, comment_, forum_

@interface.implementer(ISearchTypeMetaData)
@WithRepr
@EqHash('Name', 'MimeType')
class SearchTypeMetaData(SchemaConfigured):
	createDirectFieldProperties(ISearchTypeMetaData)
	
	@property
	def Type(self):
		return self.Name

	def __str__(self):
		return "%s,%s" % (self.Name, self.MimeType)

@interface.implementer(ISearchTypeMetaData)
def _note_metadata():
	return SearchTypeMetaData(Name=note_,
							  MimeType=(MIME_BASE + "." + note_),
							  IsUGD=True,
							  Order=5, 
							  Interface=INote)

@interface.implementer(ISearchTypeMetaData)
def _highlight_metadata():
	return SearchTypeMetaData(Name=highlight_,
							  MimeType=(MIME_BASE + "." + highlight_),
							  IsUGD=True, 
							  Order=6, 
							  Interface=IHighlight)

@interface.implementer(ISearchTypeMetaData)
def _redaction_metadata():
	return SearchTypeMetaData(Name=redaction_, 
							  MimeType=(MIME_BASE + "." + redaction_),
							  IsUGD=True, 
							  Order=7, 
							  Interface=IRedaction)

@interface.implementer(ISearchTypeMetaData)
def _transcript_metadata():
	return SearchTypeMetaData(Name=transcript_,
							  MimeType=(MIME_BASE + "." + transcript_),
							  IsUGD=True,
							  Order=8,
							  Interface=ITranscript)

@interface.implementer(ISearchTypeMetaData)
def _messageinfo_metadata():
	return SearchTypeMetaData(Name=messageinfo_,
							  MimeType=(MIME_BASE + "." + messageinfo_),
							  IsUGD=True,
							  Order=8, 
							  Interface=IMessageInfo)

@interface.implementer(ISearchTypeMetaData)
def _post_metadata():
	return SearchTypeMetaData(Name=post_,
							  MimeType=POST_MIME_TYPE,
							  IsUGD=True,
							  Order=9,
							  Interface=IPost)

@interface.implementer(ISearchTypeMetaData)
def _legacypost_metadata():
	return SearchTypeMetaData(Name=post_,
							  MimeType=(MIME_BASE + "." + post_),
							  IsUGD=True,
							  Order=9,
							  Interface=IPost)

@interface.implementer(ISearchTypeMetaData)
def _personalblogcomment_metadata():
	return SearchTypeMetaData(Name=comment_,
							  MimeType=(MIME_BASE + ".forums.personalblogcomment"),
							  IsUGD=True,
							  Order=9,
							  Interface=IPersonalBlogComment)
	
@interface.implementer(ISearchTypeMetaData)
def _generalforumcomment_metadata():
	return SearchTypeMetaData(Name=comment_,
							  MimeType=(MIME_BASE + ".forums.generalforumcomment"),
							  IsUGD=True, 
							  Order=9,
							  Interface=IGeneralForumComment)

@interface.implementer(ISearchTypeMetaData)
def _personalblogentrypost_metadata():
	return SearchTypeMetaData(Name=post_,
							  MimeType=(MIME_BASE + ".forums.personalblogentrypost"),
							  IsUGD=True,
							  Order=9,
							  Interface=IPersonalBlogEntryPost)

@interface.implementer(ISearchTypeMetaData)
def _communityheadlinepost_metadata():
	return SearchTypeMetaData(Name=post_,
							  MimeType=(MIME_BASE + ".forums.communityheadlinepost"),
							  IsUGD=True, 
							  Order=9,
							  Interface=ICommunityHeadlinePost)

@interface.implementer(ISearchTypeMetaData)
def _generalforum_metadata():
	return SearchTypeMetaData(Name=forum_,
							  MimeType=(MIME_BASE + ".forums.generalforum"),
							  IsUGD=True,
							  Order=9,
							  Interface=IGeneralForum)

@interface.implementer(ISearchTypeMetaData)
def _communityforum_metadata():
	return SearchTypeMetaData(Name=forum_,
							  MimeType=(MIME_BASE + ".forums.communityforum"),
							  IsUGD=True, 
							  Order=9,
							  Interface=ICommunityForum)

@interface.implementer(ISearchTypeMetaData)
def _nticard_metadata():
	return SearchTypeMetaData(Name=nticard_,
							  MimeType=NTI_CARD_MIME_TYPE,
							  IsUGD=False,
							  Order=4,
							  Interface=INTICardContent)

@interface.implementer(ISearchTypeMetaData)
def _book_metadata():
	return SearchTypeMetaData(Name=content_, 
							  MimeType=BOOK_CONTENT_MIME_TYPE,
							  IsUGD=False, 
							  Order=1,
							  Interface=IBookContent)

@interface.implementer(ISearchTypeMetaData)
def _legacycontent_metadata():
	return SearchTypeMetaData(Name=content_, 
							  MimeType=(MIME_BASE + "." + content_),
							  IsUGD=False,
							  Order=1,
							  Interface=IBookContent)

@interface.implementer(ISearchTypeMetaData)
def _videotranscript_metadata():
	return SearchTypeMetaData(Name=videotranscript_, 
							  MimeType=VIDEO_TRANSCRIPT_MIME_TYPE,
							  IsUGD=False, 
							  Order=2,
							  Interface=IVideoTranscriptContent)

@interface.implementer(ISearchTypeMetaData)
def _audiotranscript_metadata():
	return SearchTypeMetaData(Name=audiotranscript_,
							  MimeType=AUDIO_TRANSCRIPT_MIME_TYPE,
							  IsUGD=False, 
							  Order=3,
							  Interface=IAudioTranscriptContent)
