#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from pyramid.threadlocal import get_current_request

from zope import component

from zope.event import notify

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from nti.app.users.adapters import context_lastseen_factory

from nti.app.users.utils import set_user_creation_site
from nti.app.users.utils import set_email_verification_time
from nti.app.users.utils import safe_send_email_verification

from nti.appserver.interfaces import IUserLogonEvent
from nti.appserver.interfaces import IUserLogoutEvent

from nti.coremetadata.interfaces import UserLastSeenEvent
from nti.coremetadata.interfaces import IUserLastSeenEvent

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IWillUpdateEntityEvent
from nti.dataserver.users.interfaces import BlacklistedUsernameError
from nti.dataserver.users.interfaces import IWillCreateNewEntityEvent

from nti.dataserver.users.utils import reindex_email_verification

from nti.securitypolicy.utils import is_impersonating

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser, IWillCreateNewEntityEvent)
def _new_user_is_not_blacklisted(user, unused_event):
    """
    Verify that this new user does not exist in our blacklist of former users.
    """
    user_blacklist = component.getUtility(IUserBlacklistedStorage)
    if user_blacklist.is_user_blacklisted(user):
        raise BlacklistedUsernameError(user.username)


@component.adapter(IUser, IWillUpdateEntityEvent)
def _user_modified_from_external_event(user, event):
    profile = IUserProfile(user, None)
    email = (event.ext_value or {}).get('email')
    if profile is not None and email and profile.email != email:
        # change state of email verification
        profile.email_verified = None
        reindex_email_verification(user)
        set_email_verification_time(user, 0)
        # send email
        request = getattr(event, 'request', None) or get_current_request()
        if request is not None:
            profile.email = email  # update email so send-email can do its work
            safe_send_email_verification(user, profile, email,
                                         request=request,
                                         check=False)


@component.adapter(IUser, IObjectAddedEvent)
def _on_user_created(user, unused_event):
    set_user_creation_site(user)


@component.adapter(IUser, IObjectModifiedEvent)
def _on_user_updated(user, unused_event):
    request = get_current_request()
    if request is not None and not is_impersonating(request): 
        notify(UserLastSeenEvent(user, time.time(), request))
        

@component.adapter(IUser, IUserLogonEvent)
def _on_user_logon(user, event):
    request = getattr(event, 'request', None)
    if request is not None and not is_impersonating(request): 
        notify(UserLastSeenEvent(user, time.time(), request))


@component.adapter(IUser, IUserLogoutEvent)
def _on_user_logout(user, event):
    _on_user_logon(user, event)


@component.adapter(IUser, IUserLastSeenEvent)
def _on_user_lastseen(user, event):
    request = event.request
    if request is not None and not is_impersonating(request):
        timestamp = event.timestamp
        user.update_last_seen_time(timestamp)


@component.adapter(IUser, IObjectRemovedEvent)
def _on_user_removed(user, unused_event=None):
    container = context_lastseen_factory(user, False)
    if container:
        logger.info("Removing context last seen record(s) for user %s", user)
        container.clear()
