#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations for user externalization.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import random
import functools

from ZODB.POSException import POSError

from zope import component
from zope import interface

from nti.coremetadata.interfaces import ISystemUserPrincipal

from nti.dataserver import authorization_acl as auth

from nti.dataserver.interfaces import SYSTEM_USER_NAME

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.interfaces import IDynamicSharingTarget
from nti.dataserver.interfaces import ILinkExternalHrefOnly
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement
from nti.dataserver.interfaces import IUseNTIIDAsExternalUsername
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.interfaces import TAG_HIDDEN_IN_UI, IBlurredAvatarURL

from nti.dataserver.users.interfaces import IAvatarURL
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IAvatarChoices
from nti.dataserver.users.interfaces import IBackgroundURL
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import ICommunityProfile
from nti.dataserver.users.interfaces import IRestrictedUserProfile

from nti.dataserver.users.entity import Entity

from nti.externalization.externalization import toExternalObject
from nti.externalization.externalization import decorate_external_mapping
from nti.externalization.externalization import to_standard_external_dictionary

from nti.externalization.interfaces import IExternalObject
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.externalization.proxy import removeAllProxies

from nti.links.links import Link

from nti.mimetype.externalization import decorateMimeType

from nti.ntiids.oids import to_external_ntiid_oid

from nti.schema.interfaces import find_most_derived_interface

from nti.site.interfaces import InappropriateSiteError

from nti.property.urlproperty import UrlProperty

logger = __import__('logging').getLogger(__name__)


def _image_url(entity, avatar_iface, attr_name, view_name):
    """
    Takes into account file storage and generates Link objects
    instead of data: urls. Tightly coupled to user_profile.
    """
    with_url = avatar_iface(entity, None)
    with_url = removeAllProxies(with_url)
    url_property = getattr(type(with_url), attr_name, None)
    if isinstance(url_property, UrlProperty):
        the_file = url_property.get_file(with_url)
        if the_file:
            # View name. Coupled to the app layer
            # It's not quite possible to fully traverse to the file if the profile
            # is implemented as an annotation (and that exposes lots of internal details)
            # so we go directly to the file address
            target = to_external_ntiid_oid(the_file, add_to_connection=True)
            if target:
                link = Link(target=target,
                            target_mime_type=the_file.mimeType,
                            elements=(view_name,),
                            rel="data")
                interface.alsoProvides(link, ILinkExternalHrefOnly)
                return link
            logger.warning("Unable to produce %s for %s", attr_name, entity)
    result = getattr(with_url, attr_name, None)
    return result


def _safe_image_url(entity, avatar_iface, attr_name, view_name):
    try:
        return _image_url(entity, avatar_iface, attr_name, view_name)
    except (POSError, TypeError):
        logger.exception("Cannot get %s for entity %s", attr_name, entity)
        return None


def _is_avatar_svg(entity):
    """
    Returns whether the tnity avatar file is an SVG
    """
    with_url = IAvatarURL(entity, None)
    with_url = removeAllProxies(with_url)
    url_property = getattr(type(with_url), 'avatarURL', None)
    if isinstance(url_property, UrlProperty):
        the_file = url_property.get_file(with_url)
        return the_file and the_file.mimeType == 'image/svg+xml'


def _avatar_url(entity):
    result = _safe_image_url(entity, IAvatarURL, 'avatarURL', '@@avatar_view')
    return result


def _blurred_avatar_url(entity):
    result = _safe_image_url(entity, IBlurredAvatarURL, 'blurredAvatarURL', '@@blurred_avatar_view')
    return result


def _background_url(entity):
    result = _safe_image_url(entity, IBackgroundURL,
                             'backgroundURL', '@@background_view')
    return result


@component.adapter(ISystemUserPrincipal)
@interface.implementer(IInternalObjectExternalizer)
class _SystemUserExternalObject(object):

    def __init__(self, system_user):
        self.system_user = system_user

    def toExternalObject(self, **unused_kwargs):
        return {'Class': 'SystemUser', 'Username': SYSTEM_USER_NAME}


@interface.implementer(IExternalObject)
class _AbstractEntitySummaryExternalObject(object):

    _DECORATE = False
    _AVATAR_URL = True
    _BACKGROUND_URL = True

    def __init__(self, entity):
        self.entity = entity

    def _do_toExternalObject(self, **kwargs):
        """
        Inspects the context entity and produces its external summary form.

        :return: Standard dictionary minus Last Modified plus the properties of this class.
                 These properties include 'Username', 'avatarURL', 'realname', and 'alias'.
        """
        entity = self.entity
        kwargs.pop('decorate', None)
        extDict = to_standard_external_dictionary(entity, decorate=False, **kwargs)
        # Notice that we delete the last modified date. Because this is
        # not a real representation of the object, we don't want people to cache based
        # on it.
        extDict.pop('Last Modified', None)
        if not IUseNTIIDAsExternalUsername.providedBy(entity):
            extDict['Username'] = entity.username
        else:
            extDict['ID'] = extDict['Username'] = entity.NTIID

        if self._AVATAR_URL:
            extDict['avatarURL'] = user_avatar_url = _avatar_url(entity)
            user_blurred_url = _blurred_avatar_url(entity)
            # If our avatar url is SVG, we use it
            if not user_blurred_url and _is_avatar_svg(entity):
                user_blurred_url = user_avatar_url
            extDict['blurredAvatarURL'] = user_blurred_url

        if self._BACKGROUND_URL:
            extDict['backgroundURL'] = _background_url(entity)

        names = IFriendlyNamed(entity)
        extDict['realname'] = names.realname or entity.username
        extDict['alias'] = names.alias or names.realname or entity.username
        extDict['CreatedTime'] = getattr(entity, 'createdTime', 42)  # for migration

        extDict.__parent__ = entity.__parent__
        extDict.__name__ = entity.__name__
        # we'd like to make the ACL available. Pyramid
        # supports either a callable or the flattened list;
        # defer it until/if we need it by using a callable because
        # computing it can be expensive if the cache is cold.
        extDict.__acl__ = functools.partial(auth.ACL, entity)
        return extDict

    def toExternalObject(self, **kwargs):
        # Break this into two steps to ensure that we only try to
        # decorate the external mapping when all the objects in the hierarchy
        # have completed their work and the mapping is complete
        extDict = self._do_toExternalObject(**kwargs)
        decorate = kwargs.get('decorate', True) and self._DECORATE
        if decorate:
            decorate_external_mapping(self.entity, extDict)
        return extDict


@component.adapter(IEntity)
class _EntitySummaryExternalObject(_AbstractEntitySummaryExternalObject):
    _DECORATE = True


@component.adapter(IFriendsList)
class _FriendListSummaryExternalObject(_AbstractEntitySummaryExternalObject):

    _DECORATE = True
    _BACKGROUND_URL = False

    def _do_toExternalObject(self, **kwargs):
        extDict = super(_FriendListSummaryExternalObject, self)._do_toExternalObject(**kwargs)
        extDict['IsDynamicSharing'] = IDynamicSharingTarget.providedBy(self.entity)
        return extDict


@component.adapter(IDynamicSharingTargetFriendsList)
class _DynamicFriendListSummaryExternalObject(_FriendListSummaryExternalObject):

    _BACKGROUND_URL = True

    def _do_toExternalObject(self, **kwargs):
        extDict = super(_DynamicFriendListSummaryExternalObject, self)._do_toExternalObject(**kwargs)
        extDict['about'] = extDict['About'] = self.entity.About
        extDict['locked'] = extDict['Locked'] = self.entity.Locked
        return extDict


class _EntityExternalObject(_EntitySummaryExternalObject):

    def _do_toExternalObject(self, **kwargs):
        result = super(_EntityExternalObject, self)._do_toExternalObject(**kwargs)
        # restore last modified since we are the true representation
        result[StandardExternalFields.LAST_MODIFIED] = getattr(self.entity, 'lastModified', 0)
        return result


@component.adapter(ICommunity)
class _CommunityExternalObject(_EntityExternalObject):

    _DECORATE = True

    def __init__(self, entity):
        super(_CommunityExternalObject, self).__init__(removeAllProxies(entity))

    def _do_toExternalObject(self, **kwargs):
        result = super(_CommunityExternalObject, self)._do_toExternalObject(**kwargs)
        entity = self.entity
        most_derived_profile_iface = find_most_derived_interface(entity, ICommunityProfile)
        # Adapt to our profile
        entity = most_derived_profile_iface(entity)
        for name, field in most_derived_profile_iface.namesAndDescriptions(all=True):
            if     name in result \
                or field.queryTaggedValue(TAG_HIDDEN_IN_UI) \
                or interface.interfaces.IMethod.providedBy(field):
                continue
            field_val = field.query(entity, getattr(field, 'default', None))
            result[name] = toExternalObject(field_val)
        result['joinable'] = self.entity.joinable
        result['public'] = self.entity.public
        result['auto_subscribe'] = self.entity.auto_subscribe
        return result


@component.adapter(IFriendsList)
class _FriendsListExternalObject(_EntityExternalObject):

    _BACKGROUND_URL = False

    def _do_toExternalObject(self, **kwargs):
        extDict = super(_FriendsListExternalObject, self)._do_toExternalObject(**kwargs)
        theFriends = []
        for friend in iter(self.entity):  # iter self to weak refs and dups
            if isinstance(friend, Entity):
                # We used to be worried about personal-summary infinite recursion issues
                # here, but I think that is no longer a concern since we do not attempt
                # to decorate these on the user. Without this, the client state gets
                # messed up (due to missing fields).
                ext_name = _named_externalizer(friend)
                friend = toExternalObject(friend, name=ext_name)
                theFriends.append(friend)

        extDict['friends'] = theFriends
        extDict['CompositeGravatars'] = self._composite_gravatars()
        # We took great care to make DFLs and FLs indistinguishable from each other
        # in the external form, to make things easier for the UI. This now
        # comes back to bite us when we need to make that distinction.
        extDict['IsDynamicSharing'] = IDynamicSharingTarget.providedBy(self.entity)
        return extDict

    def _composite_gravatars(self):
        """"
        :return: A consistent list of gravatars for the users in this list. The idea is to
                shuffle them such that they are recognizable, even among different lists
                with similar memberships (that's why sorting wouldn't work).
        """
        # We do this simply by selecting 4 random users, seeded based on the name of this
        # object.
        # Is there a better seed?
        friends = [_avatar_url(x) for x in self.entity]
        if not friends:
            return ()
        rand = random.Random(hash(self.entity.username))
        return rand.sample(friends, min(4, len(friends)))


@component.adapter(IDynamicSharingTargetFriendsList)
class _DynamicFriendsListExternalObject(_FriendsListExternalObject):

    _BACKGROUND_URL = True

    def _do_toExternalObject(self, **kwargs):
        extDict = super(_DynamicFriendsListExternalObject, self)._do_toExternalObject(**kwargs)
        extDict['about'] = extDict['About'] = self.entity.About
        extDict['locked'] = extDict['Locked'] = self.entity.Locked
        return extDict


@component.adapter(IUser)
class UserSummaryExternalObject(_EntityExternalObject):

    # Even in summary (i.e. to other people), we want to publish all these fields
    # because it looks better
    public_summary_profile_fields = ('affiliation', 'home_page', 'description',
                                     'location', 'role', 'about', 'twitter',
                                     'facebook', 'linkedIn', 'instagram',
                                     'education', 'positions', 'interests')

    # These could probably be put as tags on the interface fields, but the number of
    # profile interfaces in use makes that a chore. At the moment, this is the
    # simpler option

    def _do_toExternalObject(self, **kwargs):
        extDict = super(UserSummaryExternalObject, self)._do_toExternalObject(**kwargs)
        if self.public_summary_profile_fields:
            prof = IUserProfile(self.entity)
            for f in self.public_summary_profile_fields:
                val = getattr(prof, f, None)
                extDict[f] = toExternalObject(val)
        return extDict
_UserSummaryExternalObject = UserSummaryExternalObject


@component.adapter(IUser)
class _UserAdminSummaryExternalObject(_UserSummaryExternalObject):
    """
    For admins, return the fields exposed to all users plus a few
    fields useful for administration.
    """

    @property
    def public_summary_profile_fields(self):
        result = super(_UserAdminSummaryExternalObject, self).public_summary_profile_fields
        result += ('email', 'opt_in_email_communication', 'addresses', 'phones')
        return result

    def _do_toExternalObject(self, **kwargs):
        extDict = super(_UserAdminSummaryExternalObject, self)._do_toExternalObject(**kwargs)
        extDict['lastSeenTime'] = self.entity.lastSeenTime
        extDict['lastLoginTime'] = self.entity.lastLoginTime
        return extDict
UserAdminSummaryExternalObject = _UserAdminSummaryExternalObject


@component.adapter(ICoppaUserWithoutAgreement)
class _CoppaUserSummaryExternalObject(_UserSummaryExternalObject):
    # Privacy is very important for the precious children. None of their profile
    # fields are public to other people.
    public_summary_profile_fields = ()


@component.adapter(IEntity)
@interface.implementer(IExternalObject)
class _EntityExporterExternalObject(object):

    def __init__(self, entity):
        self.entity = entity

    def toExternalObject(self, **unused_kwargs):
        result = LocatedExternalDict()
        cls = getattr(self.entity, '__external_class_name__', None)
        if cls:
            result[StandardExternalFields.CLASS] = cls
        else:
            result[StandardExternalFields.CLASS] = self.entity.__class__.__name__
        decorateMimeType(self.entity, result)
        result['Username'] = self.entity.username
        if IUseNTIIDAsExternalUsername.providedBy(self.entity):
            result[StandardExternalFields.ID] = self.entity.NTIID
        return result


# By default, when externalizing we send the minimum public data.
# A few places exist, such as the resolve user api, that can
# get the 'complete' data by asking for the registered 'personal'
# externalizer
try:
    from pyramid.threadlocal import get_current_request
except ImportError:
    def get_current_request(*unused_args):
        pass


def _is_remote_same_as_authenticated(user, req=None):
    # Warning !!! This doesn't exactly belong at this layer. Come up with
    # a better way to do this switching.
    req = get_current_request() if req is None else req
    if     req is None or req.authenticated_userid is None \
        or req.authenticated_userid != user.username:
        return False
    return True


def _named_externalizer(user, req=None):
    # Warning !!! This doesn't exactly belong at this layer. Come up with
    # a better way to do this switching.
    if _is_remote_same_as_authenticated(user, req):
        return 'personal-summary'
    return 'summary'


@component.adapter(IUser)
class _UserPersonalSummaryExternalObject(_UserSummaryExternalObject):

    def _do_toExternalObject(self, **kwargs):
        """
        :return: the externalization intended to be sent when requested by this user.
        """
        extDict = super(_UserPersonalSummaryExternalObject, self)._do_toExternalObject(**kwargs)

        def _externalize_subordinates(l, name='summary'):
            result = []
            for ent_name in l:
                # pylint: disable=unused-variable
                __traceback_info__ = name, ent_name
                if IEntity.providedBy(ent_name):
                    e = ent_name
                else:
                    try:
                        e = self.entity.get_entity(ent_name, default=self)
                        e = None if e is self else e  # Defend against no dataserver component to resolve with
                    except InappropriateSiteError:
                        # We've seen this in logging that is captured and happens
                        # after things finish running, notably nose's
                        # logcapture.
                        e = None
                if e:
                    try:
                        kw = kwargs
                        if 'name' in kw:
                            kw = kwargs.copy()
                            kw.pop('name')
                        result.append(toExternalObject(e, name=name, **kw))
                    # Thrown if we fail in certain parts of externalization
                    # (e.g., links)
                    except TypeError:
                        # Better exception?
                        # It may not be good to do this, that may hide
                        # errors that need to be corrected
                        logger.exception("Failed to externalize subordinate object %r of %r",
                                         e, self.entity)

                # It screws up the web app if we return strings here for things that do not yet or
                # do not anymore exist. Even though we've always done that.
            return result

        extDict['NotificationCount'] = self.entity.notificationCount.value

        prof = IRestrictedUserProfile(self.entity)
        extDict['email'] = prof.email
        if prof.birthdate is not None:
            # pylint: disable=no-member
            extDict['birthdate'] = prof.birthdate.isoformat()
        else:
            extDict['birthdate'] = None

        # As of 6/2018 no UIs are presenting or allowing the editing of these sharing fields (accepting,
        # rejecting, following, ignoring).  For accounts with many dynamic memberships (communities/course scopes)
        # or connections (people in contact lists) this is a bunch of wasted data. In some cases for instructors
        # of 100s of courses this leads to several hundred communities being externalized unnecessarily.  Should
        # we choose to expose this again we should do so with dynamically fetched collections.
        # Following is writable
        # following = self.entity.entities_followed
        # extDict['following'] = _externalize_subordinates(filter(_selector, following))

        # as is ignoring and accepting
        # extDict['ignoring'] = _externalize_subordinates(self.entity.entities_ignoring_shared_data_from)
        # extDict['accepting'] = _externalize_subordinates(self.entity.entities_accepting_shared_data_from)

        extDict['AvatarURLChoices'] = component.getAdapter(self.entity, IAvatarChoices).get_choices()

        extDict['Links'] = self._replace_or_add_edit_link_with_self(extDict.get('Links', ()))
        extDict['Last Modified'] = getattr(self.entity, 'lastModified', 0)

        # Ok, we did the standard profile fields. Now, find the most derived interface
        # for this profile and write the additional fields
        most_derived_profile_iface = find_most_derived_interface(prof, IRestrictedUserProfile)
        for name, field in most_derived_profile_iface.namesAndDescriptions(all=True):
            if     name in extDict or field.queryTaggedValue(TAG_HIDDEN_IN_UI) \
                or interface.interfaces.IMethod.providedBy(field):
                continue
            # Save the externalized value from the profile, or if the profile doesn't have it yet,
            # use the default (if there is one). Otherwise its None
            field_val = field.query(prof, getattr(field, 'default', None))
            extDict[name] = toExternalObject(field_val)
        return extDict

    def _replace_or_add_edit_link_with_self(self, _links):
        added = False
        _links = list(_links)
        for i, l in enumerate(_links):
            if l.rel == 'edit':
                _links[i] = Link(self.entity, rel='edit')
                added = True
        if not added:
            _links.append(Link(self.entity, rel='edit'))
        return _links


@component.adapter(IUser)
@interface.implementer(IExternalObject)
def _UserExternalObject(user):
    return component.getAdapter(user, IExternalObject, name=_named_externalizer(user))


@component.adapter(ICoppaUserWithoutAgreement)
class _CoppaUserPersonalSummaryExternalObject(_UserPersonalSummaryExternalObject):

    def _do_toExternalObject(self, **kwargs):
        extDict = super(_CoppaUserPersonalSummaryExternalObject, self)._do_toExternalObject(**kwargs)
        for k in ('affiliation', 'email', 'birthdate', 'contact_email',
                  'location', 'home_page', 'about'):
            extDict[k] = None
        return extDict


@interface.implementer(IExternalObject)
@component.adapter(ICoppaUserWithoutAgreement)
def _CoppaUserExternalObject(user):
    return component.getAdapter(user, IExternalObject, name=_named_externalizer(user))
