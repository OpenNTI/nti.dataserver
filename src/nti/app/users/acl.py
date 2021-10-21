from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.coremetadata.interfaces import IDeactivatedUser

from nti.dataserver.authentication import dynamic_memberships_that_participate_in_security

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import ACE_DENY_ALL
from nti.dataserver.interfaces import ALL_PERMISSIONS

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IACLProvider

from nti.dataserver.users.interfaces import IUserProfile


logger = __import__('logging').getLogger(__name__)


@interface.implementer(IACLProvider)
@component.adapter(IUserProfile)
class _UserProfileACLProvider(object):
    """
    ACL provider for class:`nti.dataserver.users.interfaces.IUserProfile` objects.
    """

    def __init__(self, user_profile):
        self._user_profile = user_profile
        self._user = IUser(user_profile)

    @property
    def __parent__(self):
        return self._user

    @Lazy
    def __acl__(self):
        aces = [ace_allowing(self._user.username, ALL_PERMISSIONS, type(self))]
        if not IDeactivatedUser.providedBy(self._user):
            for prin in dynamic_memberships_that_participate_in_security(self._user):
                aces.append(ace_allowing(prin, ACT_READ, type(self)))
        aces.append(ACE_DENY_ALL)
        return acl_from_aces(aces)

