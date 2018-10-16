#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic views for any user (or sometimes, entities).

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

import six

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.intid.interfaces import IIntIds

from zope.schema import getValidationErrors

from nti.app.externalization.error import raise_json_error
from nti.app.externalization.error import validation_error_to_dict

from nti.app.users import MessageFactory as _

from nti.app.users.views.view_mixins import AbstractEntityViewMixin

from nti.appserver.account_creation_views import REL_ACCOUNT_PROFILE_PREFLIGHT

from nti.appserver.dataserver_pyramid_views import GenericGetView

from nti.appserver.ugd_edit_views import UGDPutView

from nti.dataserver.authorization import ACT_UPDATE

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IUsersFolder
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.entity import Entity

from nti.dataserver.users.interfaces import IAccountProfileSchemafier
from nti.dataserver.users.interfaces import IUserProfileSchemaProvider
from nti.dataserver.users.interfaces import IDisallowMembershipOperations

from nti.dataserver.users.users_external import _avatar_url
from nti.dataserver.users.users_external import _background_url

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.links import render_link

ITEMS = StandardExternalFields.ITEMS

logger = __import__('logging').getLogger(__name__)


def _image_view(context, unused_request, func):
    """
    Redirects to the location of the actual image.
    """
    # Use a 302 response to tell clients where to go,
    # and let them cache it for awhile (a 303 is completely
    # uncachable). We expect that this method will not be
    # hit by the actual user himself, only his friends, so
    # he won't notice a stale response.

    # We use a private method to do this because we rely
    # on implementation details about the user and his data.

    url_or_link = func(context)
    if url_or_link is None:
        raise hexc.HTTPNotFound()

    if not isinstance(url_or_link, six.string_types):
        # In this case, we have a file we're hosting.
        # What happens when the user changes or removes that file?
        # we're sending direct OID links, does it still work? Or will it 404?
        url_or_link = render_link(url_or_link)

    result = hexc.HTTPFound(url_or_link)
    # Let it be cached for a bit. gravatar uses 5 minutes
    result.cache_control.max_age = 300
    result.expires = time.time() + 300
    return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IUser,
             request_method='GET',
             name='avatar')
def avatar_view(context, request):
    result = _image_view(context, request, _avatar_url)
    return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IEntity,
             request_method='GET',
             name='background')
def background_view(context, request):
    result = _image_view(context, request, _background_url)
    return result


@view_config(route_name='objects.generic.traversal',
             name='memberships',
             request_method='GET',
             context=IUser)
class UserMembershipsView(AbstractEntityViewMixin):

    def check_access(self):
        if self.remoteUser is None:
            raise hexc.HTTPForbidden()

    @Lazy
    def everyone(self):
        return Entity.get_entity('Everyone')

    def include_member(self, member):
        result = (member is not self.everyone)
        if result:
            if      ICommunity.providedBy(member) \
                and not IDisallowMembershipOperations.providedBy(member) \
                and (member.public or self.remoteUser in member):
                result = True
            elif    IDynamicSharingTargetFriendsList.providedBy(member) \
                and (self.remoteUser in member or self.remoteUser == member.creator):
                result = True
            else:
                result = False
        return result

    def get_entity_intids(self, unused_site=None):
        context = self.context
        intids = component.getUtility(IIntIds)
        # pylint: disable=no-member
        memberships = set(context.dynamic_memberships)
        memberships.update(context.friendsLists.values())
        for member in memberships:
            if self.include_member(member):
                doc_id = intids.queryId(member)
                if doc_id is not None:
                    yield doc_id

    def get_externalizer(self, entity):
        result = ''
        if ICommunity.providedBy(entity):
            result = 'summary'
        return result

    def __call__(self):
        self.check_access()
        result = self._do_call()
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IUser,
             permission=ACT_UPDATE,
             request_method='PUT')
class UserUpdateView(UGDPutView):
    """
    A concrete class to update user objects. Currently, we just exclude
    `DynamicMemberships` from the inbound user object.  We don't care
    about it and the internalization factory tries to create a None username DFL.
    """

    def readInput(self, value=None):
        value = super(UserUpdateView, self).readInput(value=value)
        value.pop('DynamicMemberships', None)
        self.validateInput(value)
        return value

    @staticmethod
    def is_valid_year(year):
        if year is None:
            return False
        elif isinstance(year, six.string_types):
            try:
                year = int(year)
            except (ValueError):
                return False
        if year < 1900:
            return False
        return True

    def validateInput(self, source):
        # Assume input is valid until shown otherwise
        # Validate that startYear < endYear for education,
        # and that they are in an appropriate range
        for education in source.get('education') or ():
            start_year = education.get('startYear', None)
            end_year = education.get('endYear', None)
            if start_year and not self.is_valid_year(start_year):
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u'Invalid education start year.'),
                                     'code': 'InvalidStartYear',
                                 },
                                 None)
            if end_year and not self.is_valid_year(end_year):
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u'Invalid education end year.'),
                                     'code': 'InvalidEndYear',
                                 },
                                 None)
            if start_year and end_year and not start_year <= end_year:
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u'Invalid education year range.'),
                                     'code': 'InvalidYearRange',
                                 },
                                 None)

        # Same thing for professional experience
        for position in source.get('positions') or ():
            start_year = position.get('startYear', None)
            end_year = position.get('endYear', None)
            if start_year and not self.is_valid_year(start_year):
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u'Invalid position start year.'),
                                     'code': 'InvalidStartYear',
                                 },
                                 None)
            if end_year and not self.is_valid_year(end_year):
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u'Invalid position end year.'),
                                     'code': 'InvalidEndYear',
                                 },
                                 None)
            if start_year and end_year and not start_year <= end_year:
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u'Invalid position year range.'),
                                     'code': 'InvalidYearRange',
                                 },
                                 None)
        return True


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IUser,
             permission=ACT_UPDATE,
             name=REL_ACCOUNT_PROFILE_PREFLIGHT,
             request_method='PUT')
class UserUpdatePreflightView(UserUpdateView):
    """
    A view to preflight profile updates, returning all validation errors if any.
    """

    def __call__(self):
        user = self.context
        result_dict = LocatedExternalDict()
        try:
            result = super(UserUpdatePreflightView, self).__call__()
        except hexc.HTTPUnprocessableEntity as response:
            if      response.json_body \
                and response.json_body.get('code') == 'SchemaNotProvided':
                # This is most likely a code issue and should be raised
                raise response
            result = response
            # We need to do this after the attempted update above.
            profile_iface = IUserProfileSchemaProvider(user).getSchema()
            profile = profile_iface(user)
            result_dict['ProfileType'] = profile_iface.__name__
            result_dict['ProfileSchema'] = IAccountProfileSchemafier(user).make_schema()
            errors = getValidationErrors(profile_iface, profile)
            errors = [validation_error_to_dict(self.request, x[1]) for x in errors or ()]
            result_dict['ValidationErrors'] = errors
            result.json_body = result_dict
        else:
            result = result_dict
            profile_iface = IUserProfileSchemaProvider(user).getSchema()
            profile = profile_iface(user)
            result_dict['ProfileType'] = profile_iface.__name__
            result_dict['ProfileSchema'] = IAccountProfileSchemafier(user).make_schema()
        self.request.environ['nti.commit_veto'] = 'abort'
        return result


@view_config(context=IUsersFolder,
             request_method='GET')
class UsersGetView(GenericGetView):

    def __call__(self):
        raise hexc.HTTPForbidden()
