#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import component

from zope.schema.interfaces import IFieldUpdatedEvent

from nti.dataserver.interfaces import IUser

from nti.dataserver.users.interfaces import IRestrictedUserProfile

from nti.dataserver.users.utils import reindex_email_invalidation
from nti.dataserver.users.utils import reindex_email_verification
from nti.dataserver.users.utils import unindex_email_invalidation
from nti.dataserver.users.utils import unindex_email_verification

from nti.schema.fieldproperty import field_name

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@component.adapter(IFieldUpdatedEvent)
def _reindex_invalid_email(event):
    if IRestrictedUserProfile.providedBy(event.inst) and \
            field_name(IRestrictedUserProfile['email_verified']) == field_name(event.field):
        profile = event.inst
        value = profile.email_verified
        user = IUser(profile)
        if value:
            reindex_email_verification(user)
            unindex_email_invalidation(user)
        elif value is None:
            unindex_email_verification(user)
            unindex_email_invalidation(user)
        else:
            unindex_email_verification(user)
            reindex_email_invalidation(user)
