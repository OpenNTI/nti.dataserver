# -*- coding: utf-8 -*-
"""
Search constants.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from nti.externalization import interfaces as ext_interfaces

from nti.mimetype.mimetype import MIME_BASE

ID 				= unicode(ext_interfaces.StandardExternalFields.ID)
HIT 			= u'Hit'
OID 			= unicode(ext_interfaces.StandardExternalFields.OID)
TYPE 			= u'Type'
BODY			= u'Body'
POST			= u'Post'
INTID			= u'INTID'
SCORE			= u'Score'
NTIID 			= unicode(ext_interfaces.StandardExternalFields.NTIID)
CLASS 			= unicode(ext_interfaces.StandardExternalFields.CLASS)
QUERY 			= u'Query'
FIELD 			= u'Field'
ITEMS			= u'Items'
CONTENT			= u'Content'
SNIPPET 		= u'Snippet'
FRAGMENTS		= u'Fragments'
FRAGMENT_COUNT	= u'Fragment Count'
TOTAL_FRAGMENTS	= u'Total Fragments'
CREATOR 		= unicode(ext_interfaces.StandardExternalFields.CREATOR)
AUTO_TAGS		= u'AutoTags'
MIME_TYPE		= unicode(ext_interfaces.StandardExternalFields.MIMETYPE)
HIT_COUNT 		= u'Hit Count'
TARGET_OID		= u'TargetOID'
MESSAGE_INFO	= u'MessageInfo'
SUGGESTIONS		= u'Suggestions'
PHRASE_SEARCH 	= u'PhraseSearch'
COLLECTION_ID	= u'CollectionId'
TYPE_COUNT		= u'Type Count'
HIT_META_DATA	= u'Hit MetaData'
TOTAL_HIT_COUNT = u'Total Hit Count'
CONTAINER_ID	= unicode(ext_interfaces.StandardExternalFields.CONTAINER_ID)
LAST_MODIFIED	= unicode(ext_interfaces.StandardExternalFields.LAST_MODIFIED)

id_				= unicode(ext_interfaces.StandardInternalFields.ID)
oid_			= u'oid'
body_ 			= u'body'
text_			= u'text'
type_			= u'type'
tags_			= u'tags'
quick_			= u'quick'
title_			= u'title'
intid_			= u'intid'
score_			= u'score'
ntiid_			= unicode(ext_interfaces.StandardInternalFields.NTIID)
color_			= u'color'
p_oid_			= u'_p_oid'
title_			= u'title'
ngrams_			= u'ngrams'
channel_		= u'channel'
section_		= u'section'
username_		= u'username'
creator_		= unicode(ext_interfaces.StandardInternalFields.CREATOR)
related_		= u'related'
content_		= u'content'
keywords_		= u'keywords'
references_		= u'references'
inReplyTo_		= u'inReplyTo'
recipients_		= u'recipients'
sharedWith_		= u'sharedWith'
selectedText_ = u'selectedText'
containerId_	= unicode(ext_interfaces.StandardInternalFields.CONTAINER_ID)
collectionId_	= u'collectionId'
last_modified_	= u'last_modified'
replacementContent_ = u'replacementContent'
redactionExplanation_ = u'redactionExplanation'
replacement_content_ = u'replacement_content'
redaction_explanation_ = u'redaction_explanation'
flattenedSharingTargetNames_ = u'flattenedSharingTargetNames'

ntiid_fields = (NTIID, ntiid_)
creator_fields = (CREATOR, creator_)
oid_fields = (OID, p_oid_, oid_, id_)
keyword_fields = (keywords_, tags_, AUTO_TAGS)
container_id_fields = (CONTAINER_ID, 'ContainerID', containerId_, 'container')
last_modified_fields =  (ext_interfaces.StandardInternalFields.LAST_MODIFIED,
						 ext_interfaces.StandardInternalFields.LAST_MODIFIEDU,
						 LAST_MODIFIED,
						 last_modified_)

nti_mimetype_prefix = MIME_BASE + '.'

note_ = u'note'
post_ = u'post'
canvas_ = u'canvas'
highlight_ = u'highlight'
redaction_ = u'redaction'
messageinfo = u'messageinfo'
messageinfo_ = u'messageinfo'
canvastextshape_ = 'canvastextshape'

ugd_indexable_type_names = (note_, post_, highlight_, redaction_, messageinfo_)
indexable_type_names = (content_,) + ugd_indexable_type_names
indexable_types_order = dict({ p:x for x, p in enumerate(indexable_type_names) })

ascending_ = u'ascending'
descending_ = u'descending'
