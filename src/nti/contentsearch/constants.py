#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Search constants.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.externalization import interfaces as ext_interfaces

from nti.mimetype.mimetype import MIME_BASE

ID 				 = unicode(ext_interfaces.StandardExternalFields.ID)
HIT 			 = u'Hit'
OID 			 = unicode(ext_interfaces.StandardExternalFields.OID)
HREF 			 = u'Href'
TYPE 			 = u'Type'
BODY			 = u'Body'
POST			 = u'Post'
INTID			 = u'INTID'
SCORE			 = u'Score'
NTIID 			 = unicode(ext_interfaces.StandardExternalFields.NTIID)
CLASS 			 = unicode(ext_interfaces.StandardExternalFields.CLASS)
QUERY 			 = u'Query'
TITLE			 = u'Title'
FIELD 			 = u'Field'
ITEMS			 = u'Items'
CONTENT			 = u'Content'
SNIPPET 		 = u'Snippet'
VIDEO_ID		 = u'VideoID'
NTI_CARD		 = u'NTICard'
FRAGMENTS		 = u'Fragments'
DESCRIPTION		 = u'Description'
TARGET_NTIID	 = u'TargetNTIID'
FRAGMENT_COUNT	 = u'Fragment Count'
TOTAL_FRAGMENTS	 = u'Total Fragments'
VIDEO_TRANSCRIPT = u'VideoTranscript'
CREATOR 		 = unicode(ext_interfaces.StandardExternalFields.CREATOR)
AUTO_TAGS		 = u'AutoTags'
MIME_TYPE		 = unicode(ext_interfaces.StandardExternalFields.MIMETYPE)
HIT_COUNT 		 = u'Hit Count'
TARGET_OID		 = u'TargetOID'
TYPE_COUNT		 = u'Type Count'
MESSAGE_INFO	 = u'MessageInfo'
SUGGESTIONS		 = u'Suggestions'
HIT_META_DATA	 = u'HitMetaData'
END_MILLISECS	 = u'EndMilliSecs'
PHRASE_SEARCH 	 = u'PhraseSearch'
COLLECTION_ID	 = u'CollectionId'
START_MILLISECS	 = u'StartMilliSecs'
TOTAL_HIT_COUNT	 = u'Total Hit Count'
TARGET_MIME_TYPE = u'Target' + ext_interfaces.StandardExternalFields.MIMETYPE
CONTAINER_ID	 = unicode(ext_interfaces.StandardExternalFields.CONTAINER_ID)
LAST_MODIFIED	 = unicode(ext_interfaces.StandardExternalFields.LAST_MODIFIED)

id_				 = unicode(ext_interfaces.StandardInternalFields.ID)
_id				 = u'_id'
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
ntiid_			 = unicode(ext_interfaces.StandardInternalFields.NTIID)
color_			 = u'color'
p_oid_			 = u'_p_oid'
title_			 = u'title'
ngrams_			 = u'ngrams'
channel_		 = u'channel'
section_		 = u'section'
videoId_		 = u'videoId'
username_		 = u'username'
creator_		 = unicode(ext_interfaces.StandardInternalFields.CREATOR)
related_		 = u'related'
content_		 = u'content'
keywords_		 = u'keywords'
references_		 = u'references'
inReplyTo_		 = u'inReplyTo'
recipients_		 = u'recipients'
sharedWith_		 = u'sharedWith'
createdTime_	 = unicode(ext_interfaces.StandardInternalFields.CREATED_TIME)
lastModified_	 = unicode(ext_interfaces.StandardInternalFields.LAST_MODIFIED)
selectedText_	 = u'selectedText'
target_ntiid_ 	 = u'target_ntiid'
containerId_	 = unicode(ext_interfaces.StandardInternalFields.CONTAINER_ID)
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
last_modified_fields = (ext_interfaces.StandardInternalFields.LAST_MODIFIED,
						ext_interfaces.StandardInternalFields.LAST_MODIFIEDU,
						LAST_MODIFIED,
						last_modified_)

created_time_fields = (ext_interfaces.StandardInternalFields.CREATED_TIME,
					   ext_interfaces.StandardExternalFields.CREATED_TIME)

text_fields = (content_, ngrams_, creator_, title_, redactionExplanation_,
			   redactionExplanation_)

book_prefix = u''
vtrans_prefix = u'vtrans_'
nticard_prefix = u'nticard_'
nti_mimetype_prefix = MIME_BASE + '.'

note_ = u'note'
post_ = u'post'
book_ = u'book'
canvas_ = u'canvas'
nticard_ = u'nticard'
highlight_ = u'highlight'
redaction_ = u'redaction'
transcript_ = 'transcript'
messageinfo = u'messageinfo'
messageinfo_ = u'messageinfo'
book_content_ = u'bookcontent'
canvastextshape_ = 'canvastextshape'
videotranscript_ = u'videotranscript'
invalid_type_ = u'++++invalidtype++++'

POST_MIME_TYPE = u'application/vnd.nextthought.forums.post'
NTI_CARD_MIME_TYPE = u'application/vnd.nextthought.nticard'
BOOK_CONTENT_MIME_TYPE = u'application/vnd.nextthought.bookcontent'
VIDEO_TRANSCRIPT_MIME_TYPE = u'application/vnd.nextthought.videotranscript'

ascending_ = u'ascending'
descending_ = u'descending'
