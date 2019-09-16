#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from PIL import Image

from PIL.ImageFilter import GaussianBlur

from six import StringIO

from zope import component

from zope.schema.interfaces import IFieldUpdatedEvent

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity

from nti.dataserver.users.interfaces import ICommunityProfile
from nti.dataserver.users.interfaces import IRestrictedUserProfile

from nti.dataserver.users.utils import reindex_email_invalidation
from nti.dataserver.users.utils import reindex_email_verification
from nti.dataserver.users.utils import unindex_email_invalidation
from nti.dataserver.users.utils import unindex_email_verification

from nti.externalization.interfaces import IObjectModifiedFromExternalEvent

from nti.property.dataurl import encode

from nti.schema.fieldproperty import field_name

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


@component.adapter(ICommunity, IObjectModifiedFromExternalEvent)
def _community_blurred_avatar(community, event):
    """
    When the community avatar is updated, create the corresponding blurredAvatarURL.
    """
    if event.external_value and 'avatarURL' in event.external_value:
        profile = ICommunityProfile(community, None)
        # We want to ensure we have an avatar here, and not a gravatar.
        avatar_file = getattr(profile, '_avatarURL', None)
        if     avatar_file is None \
            or avatar_file.mimeType == 'image/svg+xml':
            return
        data = StringIO(avatar_file.data)
        image = Image.open(data)
        # This mimics what the webapp did
        #resized_image = image.resize((560, 400), Image.ANTIALIAS)
        try:
            blurred_image = image.filter(GaussianBlur(50))
        except ValueError:
            # Unblurrable image
            profile.blurredAvatarURL = None
        else:
            blurred_bytes = StringIO()
            blurred_image.save(blurred_bytes, image.format)
            blurred_bytes.flush()
            blurred_bytes.seek(0)
            data_url = encode(blurred_bytes.read(),
                              mime_type=avatar_file.mimeType)
            profile.blurredAvatarURL = data_url
