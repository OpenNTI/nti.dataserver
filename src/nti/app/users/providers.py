from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.appserver.workspaces.interfaces import IUserWorkspaceLinkProvider
from nti.appserver.workspaces.interfaces import IGlobalWorkspaceLinkProvider

from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUsersFolder
from nti.dataserver.interfaces import IDataserverFolder

from nti.links.links import Link

from nti.traversal.traversal import find_interface

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser)
@interface.implementer(IUserWorkspaceLinkProvider)
class _SiteUsersLinkProvider(object):

    def __init__(self, user):
        self.user = user

    def links(self, unused_workspace):
        result = []
        if is_admin_or_site_admin(self.user):
            users_folder = find_interface(self.user, IUsersFolder)
            lnk = Link(users_folder, rel='SiteUsers', method='GET',
                       elements=('@@SiteUsers',))
            result.append(lnk)
        return result


@component.adapter(IUser)
@interface.implementer(IGlobalWorkspaceLinkProvider)
class _GlobalWorkspaceLinkProvider(object):

    def __init__(self, user):
        self.user = user

    def links(self, unused_workspace):
        if is_admin_or_site_admin(self.user):
            ds2 = find_interface(self.user, IDataserverFolder)
            link = Link(ds2, rel='UserInfoExtract', method='GET',
                        elements=('UserInfoExtract',))
            return [link]
        return ()
