#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.component.hooks import getSite

from nti.app.users.utils import get_user_creation_sitename
from nti.app.users.utils import get_entity_creation_sitename

from nti.coremetadata.interfaces import IAutoSubscribeMembershipPredicate

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties

logger = __import__('logging').getLogger(__name__)


@WithRepr
@interface.implementer(IAutoSubscribeMembershipPredicate)
class SiteAutoSubscribeMembershipPredicate(PersistentCreatedModDateTrackingObject):
    """
    An :class:`IAutoSubscribeMembershipPredicate` implementation that will
    accept anyone in a site (via creation site) as a member.
    """

    createDirectFieldProperties(IAutoSubscribeMembershipPredicate)

    __acl_deny_all__ = False

    __parent__ = None
    __name__ = None

    creator = None
    NTIID = alias('ntiid')

    mimeType = mime_type = 'application/vnd.nextthought.autosubscribe.siteautosubscribe'

    @property
    def entity(self):
        return self.__parent__

    def accept_user(self, user):
        """
        Returns a bool whether or not this user should be accepted.
        """
        entity_site_name = get_entity_creation_sitename(self.entity)
        # This may be during community creation such that this has
        # not yet been stored; assume current site.
        if entity_site_name is None:
            entity_site_name = getSite().__name__
        user_site_name = get_user_creation_sitename(user)
        return  entity_site_name and user_site_name \
            and entity_site_name == user_site_name
