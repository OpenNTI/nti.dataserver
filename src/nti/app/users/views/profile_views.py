#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import csv
import six

from io import BytesIO

from datetime import datetime

from functools import partial

from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

from zope import component
from zope import interface

from zope.catalog.interfaces import ICatalog

from zope.interface.interfaces import IMethod

from zope.intid.interfaces import IIntIds

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.base._compat import text_

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICoppaUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import ISiteAdminUtility
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IUsernameSubstitutionPolicy
from nti.dataserver.interfaces import ICoppaUserWithAgreementUpgraded

from nti.dataserver.users.index import CATALOG_NAME

from nti.dataserver.users.interfaces import TAG_HIDDEN_IN_UI
from nti.dataserver.users.interfaces import IImmutableFriendlyNamed
from nti.dataserver.users.interfaces import IUserProfileSchemaProvider

from nti.dataserver.users.users import User

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.internalization import update_from_external_object

from nti.schema.interfaces import find_most_derived_interface

TOTAL = StandardExternalFields.TOTAL
ITEMS = StandardExternalFields.ITEMS

logger = __import__('logging').getLogger(__name__)


def _tx_string(s):
    if s is not None and isinstance(s, six.text_type):
        s = s.encode('utf-8')
    return s


def _replace_username(username):
    substituter = component.queryUtility(IUsernameSubstitutionPolicy)
    if substituter is None:
        return username
    result = substituter.replace(username) or username
    return result


def _write_generator(generator, writer, stream):
    for line in generator():
        writer.writerow([_tx_string(x) for x in line])
    stream.flush()
    stream.seek(0)
    return stream


def _get_index_userids(ent_catalog, indexname='realname'):
    index = ent_catalog.get(indexname, None)
    result = index.ids()
    return result


def _get_index_field_value(userid, ent_catalog, indexname):
    index = ent_catalog.get(indexname, None)
    result = index.doc_value(userid) or u''
    return result


def _format_time(t):
    try:
        return datetime.fromtimestamp(t).isoformat() if t else u''
    except ValueError:
        logger.debug("Cannot parse time '%s'", t)
        return str(t)


def _format_date(d):
    try:
        return d.isoformat() if d is not None else u''
    except ValueError:
        logger.debug("Cannot parse time '%s'", d)
        return str(d)


def _get_user_info_extract(admin_user, admin_utility, all_sites=False):
    intids = component.getUtility(IIntIds)
    ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
    userids = _get_index_userids(ent_catalog)

    for iid in userids or ():
        u = intids.queryObject(iid, None)
        if not IUser.providedBy(u):
            continue

        # filter user view by site
        if      not all_sites \
            and not admin_utility.can_administer_user(admin_user, u):
                continue

        username = u.username
        userid = _replace_username(username)
        alias = _get_index_field_value(iid, ent_catalog, 'alias')
        email = _get_index_field_value(iid, ent_catalog, 'email')
        createdTime = _format_time(getattr(u, 'createdTime', 0))
        lastLoginTime = _format_time(getattr(u, 'lastLoginTime', None))
        realname = _get_index_field_value(iid, ent_catalog, 'realname')
        yield {
            'alias': _tx_string(alias),
            'email': _tx_string(email),
            'userid': _tx_string(userid),
            'realname': _tx_string(realname),
            'username': _tx_string(u.username),
            'createdTime': _tx_string(createdTime),
            'lastLoginTime': _tx_string(lastLoginTime),
        }


class AbstractUserInfoExtractView(AbstractAuthenticatedView):
    """
    params:
        all_sites - whether to include users from all sites; only available
                    to admins
    """

    def _iter_user_info_dicts(self):
        _is_site_admin = is_site_admin(self.remoteUser)
        if      not _is_site_admin \
            and not is_admin(self.remoteUser):
            raise hexc.HTTPForbidden()
        all_sites = False
        if not _is_site_admin:
            # Only admins can toggle this.
            values = CaseInsensitiveDict(self.request.params)
            value = values.get('all_sites')
            all_sites = is_true(value)
        admin_utility = component.getUtility(ISiteAdminUtility)
        return _get_user_info_extract(self.remoteUser,
                                      admin_utility,
                                      all_sites=all_sites)


@view_config(name='user_info_extract')
@view_config(name='UserInfoExtract')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               accept='text/csv',
               context=IDataserverFolder)
class UserInfoExtractCSVView(AbstractUserInfoExtractView):
    """
    A view to fetch a CSV of user info.

    params:
        all_sites - whether to include users from all sites; only available
                    to admins
    """

    def __call__(self):
        stream = BytesIO()
        fieldnames = ['username', 'userid', 'realname',
                      'alias', 'email', 'createdTime',
                      'lastLoginTime']
        csv_writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                    extrasaction='ignore')
        csv_writer.writeheader()
        for user_info in self._iter_user_info_dicts():
            csv_writer.writerow(user_info)

        response = self.request.response
        response.body = stream.getvalue()
        response.content_encoding = 'identity'
        response.content_type = 'text/csv; charset=UTF-8'
        response.content_disposition = 'attachment; filename="user_info.csv"'
        return response


@view_config(name='user_info_extract')
@view_config(name='UserInfoExtract')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               accept='application/json',
               context=IDataserverFolder)
class UserInfoExtractView(AbstractUserInfoExtractView):
    """
    A view to fetch json of user info extracts.

    params:
        all_sites - whether to include users from all sites; only available
                    to admins
    """

    def __call__(self):
        result = LocatedExternalDict()
        user_infos = tuple(self._iter_user_info_dicts())
        result[ITEMS] = user_infos
        result[TOTAL] = len(user_infos)
        return result

# opt in communication


def _parse_time(t):
    try:
        return datetime.fromtimestamp(t).isoformat() if t else u''
    except ValueError:
        logger.debug("Cannot parse time '%s'" % t)
        return str(t)


def _get_user_info(user):
    createdTime = _parse_time(getattr(user, 'createdTime', 0))
    lastModified = _parse_time(getattr(user, 'lastModified', 0))
    lastLoginTime = _parse_time(getattr(user, 'lastLoginTime', None))
    is_copaWithAgg = str(ICoppaUserWithAgreementUpgraded.providedBy(user))
    result = [createdTime, lastModified, lastLoginTime, is_copaWithAgg]
    return result


def _get_topics_info(topics_key='opt_in_email_communication', coppaOnly=False):
    header = ['username', 'userid', 'email', 'createdTime', 'lastModified',
              'lastLoginTime', 'is_copaWithAgg']
    yield header

    intids = component.getUtility(IIntIds)
    ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
    users = ent_catalog.searchResults(topics=topics_key)
    for user in users or ():
        if not IUser.providedBy(user):
            continue
        if coppaOnly and not ICoppaUser.providedBy(user):
            continue
        iid = intids.queryId(user, None)
        if iid is None:
            continue
        username = user.username
        userid = _replace_username(username)
        email = _get_index_field_value(iid, ent_catalog, 'email')
        info = [username, userid, email] + _get_user_info(user)
        yield info


@view_config(route_name='objects.generic.traversal',
             name='user_opt_in_comm',
             request_method='GET',
             context=IDataserverFolder,
             permission=nauth.ACT_NTI_ADMIN)
class UserOptInEmailCommunicationView(AbstractAuthenticatedView):

    def __call__(self):
        values = CaseInsensitiveDict(**self.request.params)
        value = values.get('coppaOnly') \
             or values.get('onlyCoppa') \
             or values.get('coppa')
        coppaOnly = is_true(value or 'F')
        generator = partial(_get_topics_info, coppaOnly=coppaOnly)

        stream = BytesIO()
        writer = csv.writer(stream)
        response = self.request.response
        response.content_encoding = 'identity'
        response.content_type = 'text/csv; charset=UTF-8'
        response.content_disposition = 'attachment; filename="opt_in.csv"'
        response.body_file = _write_generator(generator, writer, stream)
        return response


@view_config(route_name='objects.generic.traversal',
             name='user_email_verified',
             request_method='GET',
             context=IDataserverFolder,
             permission=nauth.ACT_NTI_ADMIN)
class UserEmailVerifiedView(AbstractAuthenticatedView):

    def __call__(self):
        values = CaseInsensitiveDict(**self.request.params)
        value = values.get('coppaOnly') \
             or values.get('onlyCoppa') \
             or values.get('coppa')
        coppaOnly = is_true(value or 'F')
        generator = partial(_get_topics_info,
                            topics_key='email_verified',
                            coppaOnly=coppaOnly)

        stream = BytesIO()
        writer = csv.writer(stream)
        response = self.request.response
        response.content_encoding = 'identity'
        response.content_type = 'text/csv; charset=UTF-8'
        response.content_disposition = 'attachment; filename="verified_email.csv"'
        response.body_file = _write_generator(generator, writer, stream)
        return response


# user profile


def _get_profile_info(coppaOnly=False):
    header = ['username', 'userid', 'email', 'contact_email', 'createdTime',
              'lastModified', 'lastLoginTime', 'is_copaWithAgg']
    yield header

    dataserver = component.getUtility(IDataserver)
    users_folder = IShardLayout(dataserver).users_folder
    intids = component.getUtility(IIntIds)
    ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

    for user in users_folder.values():
        if     not IUser.providedBy(user) \
            or (coppaOnly and not ICoppaUser.providedBy(user)):
            continue

        iid = intids.queryId(user, None)
        if iid is None:
            continue

        username = user.username
        userid = _replace_username(username)
        email = _get_index_field_value(iid, ent_catalog, 'email')
        contact_email = _get_index_field_value(iid, ent_catalog, 'contact_email') or email
        info = [username, userid, email, contact_email] + _get_user_info(user)
        yield info


@view_config(route_name='objects.generic.traversal',
             name='user_profile_info',
             request_method='GET',
             context=IDataserverFolder,
             permission=nauth.ACT_NTI_ADMIN)
class UserProfileInfoView(AbstractAuthenticatedView):

    def __call__(self):
        request = self.request
        values = CaseInsensitiveDict(**request.params)
        coppaOnly = is_true(values.get('coppaOnly', 'F'))
        generator = partial(_get_profile_info, coppaOnly=coppaOnly)

        stream = BytesIO()
        writer = csv.writer(stream)
        response = self.request.response
        response.content_encoding = 'identity'
        response.content_type = 'text/csv; charset=UTF-8'
        response.content_disposition = 'attachment; filename="profile.csv"'
        response.body_file = _write_generator(generator, writer, stream)
        return response


# user profile


def _get_inactive_accounts(max_days=365):
    header = ['username', 'userid', 'realname',
              'email', 'createdTime', 'lastLoginTime']
    yield header

    dataserver = component.getUtility(IDataserver)
    _users = IShardLayout(dataserver).users_folder
    intids = component.getUtility(IIntIds)
    ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

    now = datetime.utcnow()
    for user in _users.values():
        if not IUser.providedBy(user):
            continue

        iid = intids.queryId(user, None)
        if iid is None:
            continue

        try:
            lastLoginTime = getattr(user, 'lastLoginTime', None)
            if lastLoginTime:
                lastLoginTime = datetime.utcfromtimestamp(lastLoginTime)
        except ValueError:
            logger.error("Cannot parse %s for user %s", lastLoginTime, user)
            continue

        if lastLoginTime and (now - lastLoginTime).days < max_days:
            continue

        username = user.username
        userid = _replace_username(username)
        email = _get_index_field_value(iid, ent_catalog, 'email')
        createdTime = _parse_time(getattr(user, 'createdTime', 0))
        realname = _get_index_field_value(iid, ent_catalog, 'realname')
        lastLoginTime = lastLoginTime.isoformat() if lastLoginTime else None
        info = [username, userid, realname, email, createdTime, lastLoginTime]
        yield info


@view_config(route_name='objects.generic.traversal',
             name='inactive_accounts',
             request_method='GET',
             context=IDataserverFolder,
             permission=nauth.ACT_NTI_ADMIN)
class InactiveAccountsView(AbstractAuthenticatedView):

    def __call__(self):
        generator = _get_inactive_accounts
        stream = BytesIO()
        writer = csv.writer(stream)
        response = self.request.response
        response.content_encoding = 'identity'
        response.content_type = 'text/csv; charset=UTF-8'
        response.content_disposition = 'attachment; filename="inactive.csv"'
        response.body_file = _write_generator(generator, writer, stream)
        return response


def allowed_fields(user):
    profile_iface = IUserProfileSchemaProvider(user).getSchema()
    profile = profile_iface(user)
    possibilities = interface.providedBy(profile)
    profile_schema = find_most_derived_interface(profile,
                                                 profile_iface,
                                                 possibilities=possibilities)

    result = {}
    for k, v in profile_schema.namesAndDescriptions(all=True):
        if IMethod.providedBy(v) or v.queryTaggedValue(TAG_HIDDEN_IN_UI):
            continue
        result[k] = v
    return profile, result


@view_config(route_name='objects.generic.traversal',
             name='user_profile_update',
             request_method='POST',
             renderer='rest',
             context=IDataserverFolder,
             permission=nauth.ACT_NTI_ADMIN)
class UserProfileUpdateView(AbstractAuthenticatedView,
                            ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        result = super(UserProfileUpdateView, self).readInput(value)
        result = CaseInsensitiveDict(result)
        return result

    def __call__(self):
        values = self.readInput()
        authenticated_userid = self.remoteUser.username
        username = values.get('username') \
                or values.get('user') \
                or authenticated_userid
        user = User.get_user(username)
        if user is None or not IUser.providedBy(user):
            raise hexc.HTTPUnprocessableEntity('User not found')

        external = {}
        profile, fields = allowed_fields(user)
        for name, sch_def in fields.items():
            value = values.get(name, None)
            if value is not None:
                value = text_(value)
                if value:
                    external[name] = sch_def.fromUnicode(value)
                else:
                    external[name] = None

        restore_iface = False
        if IImmutableFriendlyNamed.providedBy(user):
            restore_iface = True
            interface.noLongerProvides(user, IImmutableFriendlyNamed)

        update_from_external_object(user, external)
        if restore_iface:
            interface.alsoProvides(user, IImmutableFriendlyNamed)

        result = LocatedExternalDict()
        result['External'] = external
        result['Profile'] = profile.__class__.__name__
        result['Allowed Fields'] = list(fields.keys())
        result['Summary'] = to_external_object(user, name="summary")
        return result
