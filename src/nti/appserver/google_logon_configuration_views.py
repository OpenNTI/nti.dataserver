#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.interfaces import IRequest

from pyramid.view import view_config
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider
from nti.appserver.interfaces import IGoogleLogonLookupUtility
from nti.appserver.interfaces import IGoogleLogonSettings

from nti.appserver.logon import GoogleLogonSettings
from nti.appserver.logon import GoogleLogonLookupUtility
from nti.appserver.logon import SimpleUnauthenticatedUserGoogleLinkProvider
from nti.appserver.logon import SimpleMissingUserGoogleLinkProvider

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IMissingUser

from nti.site import unregisterUtility

from nti.site.localutility import install_utility


logger = __import__('logging').getLogger(__name__)


GOOGLE_LOGON_LOOKUP_NAME = u'GoogleLogonLookupUtility'
GOOGLE_LOGON_SETTINGS_NAME = u'GoogleLogonSettings'


@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class GoogleLogonConfigurationView(AbstractAuthenticatedView):
    """
    Enable or disable google oauth logon for a site.
    """

    @Lazy
    def site(self):
        return getSite()

    @Lazy
    def site_manager(self):
        return self.site.getSiteManager()

    def _params(self):
        """
        If lookup_by_email is effectively true we would look up user with the email and would use the email as username,
        otherwise we would look up user with external identity and create a unique random username for the email.
        """
        params = CaseInsensitiveDict(self.request.params)
        params['lookup_by_email'] = is_true(params.get('lookup_by_email'))

        rd = params.get('restricted_domain')
        params['restricted_domain'] = params['restricted_domain'].strip() or None if rd else None
        return params

    def _register_missing_user_link_provider(self):
        self.site_manager.registerSubscriptionAdapter(SimpleMissingUserGoogleLinkProvider,
                                                      (IMissingUser, IRequest),
                                                      ILogonLinkProvider)

    def _unregister_missing_user_link_provider(self):
        self.site_manager.unregisterSubscriptionAdapter(SimpleMissingUserGoogleLinkProvider,
                                                        (IMissingUser, IRequest),
                                                        ILogonLinkProvider)

    def _register_unauthenticated_user_link_provider(self):
        self.site_manager.registerSubscriptionAdapter(SimpleUnauthenticatedUserGoogleLinkProvider,
                                                      (IRequest,),
                                                      IUnauthenticatedUserLinkProvider)

    def _unregister_unauthenticated_user_link_provider(self):
        self.site_manager.unregisterSubscriptionAdapter(SimpleUnauthenticatedUserGoogleLinkProvider,
                                                        (IRequest,),
                                                        IUnauthenticatedUserLinkProvider)

    def _get_local_utility(self, iface):
        obj = component.queryUtility(iface, context=self.site)
        if obj is None or getattr(obj, '__parent__', None) != self.site_manager:
            return None
        return obj

    def _register_lookup_utility(self, lookup_by_email=False):
        obj = GoogleLogonLookupUtility(lookup_by_email=lookup_by_email)
        obj.__name__ = GOOGLE_LOGON_LOOKUP_NAME
        install_utility(obj,
                        utility_name=obj.__name__,
                        provided=IGoogleLogonLookupUtility,
                        local_site_manager=self.site_manager)
        return obj

    def _register_settings_utility(self, restricted_domain=None):
        obj = GoogleLogonSettings(restricted_domain)
        obj.__name__ = GOOGLE_LOGON_SETTINGS_NAME
        install_utility(obj,
                        utility_name=obj.__name__,
                        provided=IGoogleLogonSettings,
                        local_site_manager=self.site_manager)
        return obj

    def _unregister_local_utility(self, iface):
        obj = self._get_local_utility(iface)
        if obj is not None:
            del self.site_manager[obj.__name__]
            unregisterUtility(self.site_manager, obj, iface)

    @view_config(request_method='POST',
                 name="enable_google_logon")
    def enable(self):
        logger.info("Enabling google oauth logon for site (%s) by username=%s", self.site.__name__, self.remoteUser)
        params = self._params()

        # Logon lookup utility.
        lookup = self._get_local_utility(IGoogleLogonLookupUtility)
        if lookup is None:
            lookup = self._register_lookup_utility(lookup_by_email=params['lookup_by_email'])
        else:
            lookup.lookup_by_email = params['lookup_by_email']

        # Logon settings utility.
        settings = self._get_local_utility(IGoogleLogonSettings)
        if settings is None:
            settings = self._register_settings_utility(restricted_domain=params['restricted_domain'])
        else:
            settings.hd = params['restricted_domain']

        # Missing user link provider.
        self._register_missing_user_link_provider()

        # Unauthenticated user link provider.
        self._register_unauthenticated_user_link_provider()

        return {
            'lookup_by_email': lookup.lookup_by_email,
            'restricted_domain': settings.hd
        }

    @view_config(request_method='POST',
                 name="disable_google_logon")
    def disable(self):
        logger.info("Disabling google oauth logon for site (%s) by username=%s", self.site.__name__, self.remoteUser)

        self._unregister_local_utility(IGoogleLogonLookupUtility)

        self._unregister_local_utility(IGoogleLogonSettings)

        self._unregister_missing_user_link_provider()

        self._unregister_unauthenticated_user_link_provider()
        return hexc.HTTPNoContent()
