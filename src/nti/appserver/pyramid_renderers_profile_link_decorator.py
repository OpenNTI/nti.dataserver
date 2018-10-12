#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A decorator for various user profile-type links.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface
from zope import component

from pyramid.threadlocal import get_current_request

from nti.appserver._util import link_belongs_to_user

from nti.appserver.account_creation_views import REL_ACCOUNT_PROFILE_SCHEMA
from nti.appserver.account_creation_views import REL_ACCOUNT_PROFILE_PREFLIGHT

from nti.appserver.user_activity_views import REL_USER_ACTIVITY

from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import Singleton

from nti.dataserver.interfaces import IUser

from nti.links.links import Link

logger = __import__('logging').getLogger(__name__)


# These imports are broken out explicitly for speed (avoid runtime
# attribute lookup)
LINKS = StandardExternalFields.LINKS


@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class ProfileLinkDecorator(Singleton):

    def decorateExternalMapping(self, context, mapping):
        request = get_current_request()
        the_links = mapping.setdefault(LINKS, [])
        if request is not None and context.username == request.authenticated_userid:
            for rel in (REL_ACCOUNT_PROFILE_SCHEMA,
                        REL_ACCOUNT_PROFILE_PREFLIGHT):
                # You get your own profile schema
                link = Link(context,
                            rel=rel,
                            elements=('@@%s' % rel,))
                link_belongs_to_user(link, context)
                the_links.append(link)

        # TODO: This is action at a distance. Refactor these to be cleaner.
        # Primary reason this are here: speed.
        link = Link(context,
                    rel=REL_USER_ACTIVITY,
                    elements=(REL_USER_ACTIVITY,))
        link_belongs_to_user(link, context)
        the_links.append(link)
