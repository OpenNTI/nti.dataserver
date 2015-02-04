#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search constants.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import StandardInternalFields

from nti.mimetype.mimetype import MIME_BASE

ID 				 = unicode(StandardExternalFields.ID)
HIT 			 = u'Hit'
HITS 			 = u'Hits'
OID 			 = unicode(StandardExternalFields.OID)
TYPE 			 = u'Type'
BODY			 = u'Body'
POST			 = u'Post'
FORUM			 = u'Forum'
NTIID 			 = unicode(StandardExternalFields.NTIID)
CLASS 			 = unicode(StandardExternalFields.CLASS)
FIELD 			 = u'Field'
ITEMS			 = u'Items'
QUERY			 = u'Query'
SNIPPET			 = u'Snippet'
CONTENT			 = u'Content'
NTI_CARD		 = u'NTICard'
FRAGMENTS		 = u'Fragments'
DESCRIPTION		 = u'Description'
SUGGESTIONS		 = u'Suggestions'
SEARCH_QUERY	 = u'SearchQuery'
FRAGMENT_COUNT	 = u'Fragment Count'
TOTAL_FRAGMENTS	 = u'Total Fragments'
AUDIO_TRANSCRIPT = u'AudioTranscript'
VIDEO_TRANSCRIPT = u'VideoTranscript'
CREATOR 		 = unicode(StandardExternalFields.CREATOR)
AUTO_TAGS		 = u'AutoTags'
MIME_TYPE		 = unicode(StandardExternalFields.MIMETYPE)
HIT_COUNT 		 = u'Hit Count'
MESSAGE_INFO	 = u'MessageInfo'
SUGGESTIONS		 = u'Suggestions'
HIT_META_DATA	 = u'HitMetaData'
PHRASE_SEARCH 	 = u'PhraseSearch'
CONTAINER_ID	 = unicode(StandardExternalFields.CONTAINER_ID)
LAST_MODIFIED	 = unicode(StandardExternalFields.LAST_MODIFIED)
CREATED_TIME 	 = unicode(StandardExternalFields.CREATED_TIME)

id_				 = unicode(StandardInternalFields.ID)
acl_			 = u'acl'
oid_			 = u'oid'
body_ 			 = u'body'
text_			 = u'text'
href_			 = u'href'
type_			 = u'type'
tags_			 = u'tags'
quick_			 = u'quick'
title_			 = u'title'
intid_			 = u'intid'
score_			 = u'score'
docnum_			 = u'docnum'
ntiid_			 = unicode(StandardInternalFields.NTIID)
color_			 = u'color'
p_oid_			 = u'_p_oid'
title_			 = u'title'
ngrams_			 = u'ngrams'
channel_		 = u'channel'
section_		 = u'section'
videoId_		 = u'videoId'
username_		 = u'username'
creator_		 = unicode(StandardInternalFields.CREATOR)
related_		 = u'related'
content_		 = u'content'
keywords_		 = u'keywords'
references_		 = u'references'
inReplyTo_		 = u'inReplyTo'
recipients_		 = u'recipients'
sharedWith_		 = u'sharedWith'
createdTime_	 = unicode(StandardInternalFields.CREATED_TIME)
lastModified_	 = unicode(StandardInternalFields.LAST_MODIFIED)
selectedText_	 = u'selectedText'
target_ntiid_ 	 = u'target_ntiid'
containerId_	 = unicode(StandardInternalFields.CONTAINER_ID)
collectionId_	 = u'collectionId'
last_modified_	 = u'last_modified'
end_timestamp_	 = u'end_timestamp'
start_timestamp_ = u'start_timestamp'
replacementContent_ = u'replacementContent'
replacement_content_ = u'replacement_content'
redactionExplanation_ = u'redactionExplanation'
redaction_explanation_ = u'redaction_explanation'
flattenedSharingTargetNames_ = u'flattenedSharingTargetNames'

ntiid_fields = (NTIID, ntiid_)
tag_fields = (tags_, AUTO_TAGS)
creator_fields = (CREATOR, creator_)
oid_fields = (OID, p_oid_, oid_, id_)
container_id_fields = (CONTAINER_ID, 'ContainerID', containerId_, 'container')
last_modified_fields = (StandardInternalFields.LAST_MODIFIED,
						StandardInternalFields.LAST_MODIFIEDU,
						LAST_MODIFIED,
						last_modified_)

created_time_fields = (StandardInternalFields.CREATED_TIME,
					   StandardExternalFields.CREATED_TIME)

book_prefix = u''
atrans_prefix = u'atrans_'
vtrans_prefix = u'vtrans_'
nticard_prefix = u'nticard_'
nti_mimetype_prefix = MIME_BASE + '.'

note_ = u'note'
post_ = u'post'
book_ = u'book'
forum_ = u'forum'
canvas_ = u'canvas'
comment_ = u'comment'
nticard_ = u'nticard'
highlight_ = u'highlight'
redaction_ = u'redaction'
transcript_ = 'transcript'
messageinfo = u'messageinfo'
messageinfo_ = u'messageinfo'
book_content_ = u'bookcontent'
canvastextshape_ = 'canvastextshape'
audiotranscript_ = u'videotranscript'
videotranscript_ = u'videotranscript'
invalid_type_ = u'++++invalidtype++++'

POST_MIME_TYPE = u'application/vnd.nextthought.forums.post'
NTI_CARD_MIME_TYPE = u'application/vnd.nextthought.nticard'
BOOK_CONTENT_MIME_TYPE = u'application/vnd.nextthought.bookcontent'
AUDIO_TRANSCRIPT_MIME_TYPE = u'application/vnd.nextthought.audiotranscript'
VIDEO_TRANSCRIPT_MIME_TYPE = u'application/vnd.nextthought.videotranscript'

ascending_ = u'ascending'
descending_ = u'descending'
