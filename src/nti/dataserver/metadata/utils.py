#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.intid.interfaces import IIntIds

from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.dataserver.metadata.index import IX_CREATOR
from nti.dataserver.metadata.index import IX_TAGGEDTO
from nti.dataserver.metadata.index import IX_SHAREDWITH
from nti.dataserver.metadata.index import IX_REVSHAREDWITH
from nti.dataserver.metadata.index import IX_REPLIES_TO_CREATOR

from nti.dataserver.metadata.interfaces import IPrincipalMetadataObjects

from nti.zodb import isBroken

from nti.zope_catalog.interfaces import IKeywordIndex


def queryId(obj, intids=None):
    intids = component.queryUtility(IIntIds) if intids is None else intids
    return intids.queryId(obj) if intids is not None else None
get_iid = queryId


def user_messageinfo_iter_objects(user, broken=None):
    storage = IUserTranscriptStorage(user)
    for transcript in storage.transcripts:
        for message in transcript.Messages:
            if broken is not None and isBroken(message):
                broken.append(message)
            else:
                yield message


def user_messageinfo_iter_intids(user, intids=None, broken=None):
    for message in user_messageinfo_iter_objects(user, broken=broken):
        uid = queryId(message, intids=intids)
        if uid is not None:
            yield uid


def delete_entity_metadata(catalog, username):
    result = 0
    if catalog is not None:
        username = username.lower()
        index = catalog[IX_CREATOR]
        query = {
            IX_CREATOR: {'any_of': (username,)}
        }
        for uid in catalog.apply(query) or ():
            index.unindex_doc(uid)
            result += 1
    return result


def clear_replies_to_creator(catalog, username, intids=None):
    """
    When a creator is removed, all of the things that were direct
    replies to that creator are now \"orphans\", with a value
    for ``inReplyTo``. We clear out the index entry for ``repliesToCreator``
    for this entity in that case.

    The same scenario holds for things that were shared directly
    to that user.
    """
    if catalog is None:
        # Not installed yet
        return
    intids = component.getUtility(IIntIds) if intids is None else intids
    # These we can simply remove, this creator doesn't exist anymore
    for ix_name in (IX_REPLIES_TO_CREATOR, IX_TAGGEDTO):
        index = catalog[ix_name]
        query = {
            ix_name: {'any_of': (username,)}
        }
        for doc_id in catalog.apply(query) or ():
            index.unindex_doc(doc_id)

    # These, though, may still be shared, so we need to reindex them
    index = catalog[IX_SHAREDWITH]
    query = {
        IX_SHAREDWITH: {'any_of': (username,)}
    }
    for doc_id in catalog.apply(query) or ():
        obj = intids.queryObject(doc_id)
        if obj is not None:
            index.index_doc(doc_id, obj)

    index = catalog[IX_REVSHAREDWITH]
    if IKeywordIndex.providedBy(index):
        index.remove_words((username,))


def get_principal_metadata_objects(principal, broken=None):
    predicates = component.subscribers((principal,), IPrincipalMetadataObjects)
    for predicate in list(predicates):
        for obj in predicate.iter_objects():
            if broken is not None and isBroken(obj):
                broken.append(obj)
            else:
                yield obj
