#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.lifecycleevent.interfaces import IObjectAddedEvent

from pyramid.threadlocal import get_current_request

from nti.app.users.utils import set_user_creation_site
from nti.app.users.utils import set_email_verification_time
from nti.app.users.utils import safe_send_email_verification

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IWillUpdateEntityEvent
from nti.dataserver.users.interfaces import BlacklistedUsernameError
from nti.dataserver.users.interfaces import IWillCreateNewEntityEvent

from nti.dataserver.users.utils import reindex_email_verification

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
        profile.email_verified = False
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
