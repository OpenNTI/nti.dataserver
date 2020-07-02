#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

from zope import component

from nti.app.externalization.error import raise_json_error

from nti.app.mentions import MessageFactory as _

from nti.coremetadata.interfaces import IMentionable

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IStreamChangeAcceptedByUser

from nti.dataserver.mentions.interfaces import IPreviousMentions

from nti.dataserver.users import User

from nti.ntiids.oids import to_external_ntiid_oid

from nti.schema.interfaces import IBeforeSequenceAssignedEvent

logger = __import__("logging").getLogger(__name__)


@component.adapter(tuple, IMentionable, IBeforeSequenceAssignedEvent)
def _validate_mentions(ext_value, mentionable, event):
    """
    Need to validate that each mentioned items is a valid user (for
    now, though other entities may be supported later.
    """

    # Since there may be more than one field that's a tuple
    if event.name != "__st_mentions_st":
        return

    for username in ext_value or ():
        user = User.get_user(username)
        if not IUser.providedBy(user):
            raise_json_error(get_current_request(),
                             hexc.HTTPUnprocessableEntity,
                             {
                                 "message": _(u"User not found."),
                                 "field": "mentions",
                                 "code": "UserNotFoundError",
                                 "username": username,
                                 "value": ext_value,
                             },
                             None)

    # Used during modifications to calculate what the newly
    # added mentions were.
    IPreviousMentions(mentionable).mentions = mentionable.mentions


def _is_newly_mentioned(user, change):
    mentions_info = getattr(change, 'mentions_info', None)

    if mentions_info is None:
        return False

    return user in change.mentions_info.new_effective_mentions


@component.adapter(IStreamChangeAcceptedByUser)
def _user_notified(event):

    user = event.target
    change = event.object
    mentionable = IMentionable(change.object, None)
    if mentionable is not None \
            and _is_newly_mentioned(user, change):
        IPreviousMentions(mentionable).add_notification(user)
        mentionable_oid = to_external_ntiid_oid(mentionable)
        logger.info("User %s sent notification of mention for object %s (%s)",
                    user.username, mentionable_oid, change.type)
