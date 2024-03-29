#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import nameparser

from zope import component
from zope import interface

from zope.component.hooks import getSite

from zope.i18n import translate

from zope.i18n.interfaces import IUserPreferredLanguages

from pyramid.threadlocal import get_current_request

from nti.appserver import MessageFactory as _

from nti.appserver.interfaces import ILogonPong
from nti.appserver.interfaces import IModeratorDealtWithFlag

from nti.appserver.link_providers import provide_links

from nti.appserver.logon import REL_INITIAL_WELCOME_PAGE
from nti.appserver.logon import REL_INITIAL_TOS_PAGE
from nti.appserver.logon import REL_INVALID_EMAIL
from nti.appserver.logon import REL_INVALID_CONTACT_EMAIL

from nti.common.nameparser import constants as np_constants

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IContainerContext
from nti.dataserver.interfaces import IContextAnnotatable
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import Singleton

from nti.securitypolicy.utils import is_impersonating

logger = __import__('logging').getLogger(__name__)


@component.adapter(ILogonPong)
@interface.implementer(IExternalObjectDecorator)
class _SiteNameAdder(Singleton):

    def decorateExternalObject(self, unused_context, mapping):
        site = getSite()
        if site is not None:
            mapping['Site'] = site.__name__


@component.adapter(IContextAnnotatable)
@interface.implementer(IExternalMappingDecorator)
class _ContainerContextDecorator(Singleton):
    """
    For :class:`~.IContextAnnotatable` objects, decorate the
    result with the context_id.
    """

    def decorateExternalMapping(self, context, mapping):
        container_context = IContainerContext(context, None)
        if container_context:
            mapping['ContainerContext'] = container_context.context_id


@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _EnglishFirstAndLastNameDecorator(Singleton):
    """
    If a user's first preferred language is English,
    then assume that they provided a first and last name and return that
    in the profile data.

    .. note::
            This is an incredibly Western and even US centric way of
            looking at things. The restriction to those that prefer
            English as their language is an attempt to limit the damage.
    """

    def decorateExternalMapping(self, original, external):
        realname = external.get('realname')
        if not realname or '@' in realname or realname == external.get('ID'):
            return

        preflangs = IUserPreferredLanguages(original, None)
        if preflangs and 'en' == (preflangs.getPreferredLanguages() or (None,))[0]:
            # FIXME: Duplicated from users.user_profile
            # CFA: another suffix we see from certain financial quorters
            constants = np_constants(extra_suffixes=('cfa',))
            human_name = nameparser.HumanName(realname, constants=constants)
            last = human_name.last or human_name.first
            first = human_name.first or human_name.last
            if first:
                external['NonI18NFirstName'] = first
                external['NonI18NLastName'] = last


@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _AuthenticatedUserLinkAdder(Singleton):
    """
    When we decorate an user, if the user is ourself, we want to provide
    the same links that we would at logon time, mostly as a convenience
    to the client.
    """

    def _filtered_links(self, links, request, userid):
        if links and (is_impersonating(request) or userid.endswith('@nextthought.com')):
            return [x for x in links if x.rel not in (REL_INITIAL_WELCOME_PAGE,
                                                      REL_INITIAL_TOS_PAGE,
                                                      REL_INVALID_EMAIL,
                                                      REL_INVALID_CONTACT_EMAIL)]
        return links

    def decorateExternalMapping(self, original, external):
        request = get_current_request()
        if not request:
            return

        userid = request.authenticated_userid
        if not userid or original.username != userid:
            return

        links = list(external.get(StandardExternalFields.LINKS, ()))
        links.extend(provide_links(original, request))
        links = self._filtered_links(links, request, userid)

        external[StandardExternalFields.LINKS] = links


@component.adapter(IDeletedObjectPlaceholder)
@interface.implementer(IExternalObjectDecorator)
class _DeletedObjectPlaceholderDecorator(Singleton):
    """
    Replaces the title, description, and body of deleted objects with I18N strings.
    Cleans up some other data too that we don't want out.
    """

    _message = _(u"This item has been deleted.")

    _moderator_message = _(u"This item has been deleted by the moderator.")

    def decorateExternalObject(self, original, external):
        request = get_current_request()
        deleted_by_moderator = IModeratorDealtWithFlag.providedBy(original)
        if deleted_by_moderator:
            message = self._moderator_message
        else:
            message = self._message
        message = translate(message, context=request)

        if 'title' in external:
            external['title'] = message
        if 'description' in external:
            external['description'] = message
        if 'body' in external:
            external['body'] = [message]
        if 'tags' in external:
            external['tags'] = ()

        if StandardExternalFields.LINKS in external:
            # These may or may not be rendered at this point
            links = []
            for link in external[StandardExternalFields.LINKS]:
                try:
                    rel = link['rel']
                except KeyError:
                    rel = link.rel
                if rel in ('replies',):
                    # We want to allow access to non-deleted children
                    # XXX FIXME: This should probably be a per-interface
                    # whitelist?
                    links.append(link)
            external[StandardExternalFields.LINKS] = links

        # Note that we are still externalizing with the original class and mimetype values;
        # to do otherwise would almost certainly break client assumptions about the type
        # of data the APIs return.
        # But we do expose secondary information about this state:
        external['Deleted'] = True
        if deleted_by_moderator:
            external['DeletedByModerator'] = True

