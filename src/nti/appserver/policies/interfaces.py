# -*- coding: utf-8 -*-
"""
Site policies interfaces

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,no-value-for-parameter

from zope import interface

from zope.schema import NativeStringLine

from nti.schema.field import Bool
from nti.schema.field import TextLine


class ISitePolicyUserEventListener(interface.Interface):
    """
    Register instances of these as utilities by the name of the site
    they should apply to.
    """

    DISPLAY_NAME = TextLine(title=u'Optional human-readable name for the site.',
                            description=u'Do not access directly, use :func:`nti.appserver.policies.site_polices.guess_site_display_name`',
                            required=False,
                            default=None)

    BRAND = TextLine(title=u'The brand name for this site.',
                     required=True,
                     default=u'NextThought')

    GOOGLE_AUTH_USER_CREATION = Bool(title=u'Is Google OAuth creation allowed on this site?',
                                     default=True,
                                     required=False)

    LANDING_PAGE_NTIID = NativeStringLine(title=u'Sent in the nti.landing_page cookie',
                                          default=None,
                                          required=False)

    def map_validation_exception(incoming_data, exception):
        """
        Gives a site policy a chance to change an exception being returned
        during validation.
        """

    def user_will_update_new(user, event):
        """
        Handler for the IWillUpdateNewEntityEvent, called
        before creation is complete or the user is updated.
        """

    def user_created(user, event):
        """
        Called when a user is created.
        """

    def user_did_logon(user, event):
        """
        Called when a user logs on in response to a IUserLogonEvent.
        """

    def user_created_with_request(user, event):
        """
        Called when a user is created in the scope of an interactive
        request (after user_created).
        """

    def user_will_create(user, event):
        """
        Called just before a user is created. Do most validation here.
        """

    # I'm not entirely sure this belongs here. Might want to rethink
    # this a lot
    def upgrade_user(user):
        """
        Transition a user from a limited form to the next lest limited forrm.
        Specifically intended to deal with providing coppa consent.
        """


class ICommunitySitePolicyUserEventListener(ISitePolicyUserEventListener):
    """
    A type of site policy that places all accounts created by that site into a
    particular community. This :class:`ISiteCommunity` should only be used
    by that site. All site policies will be an implementation of this interface
    to preserve backwards compatibility.
    """

    COM_USERNAME = TextLine(title=u'The globally resolvable name of a community, or None',
                            required=False,
                            default=None)

    COM_ALIAS = TextLine(title=u'The alias for the site community',
                         required=False,
                         default=None)

    COM_REALNAME = TextLine(title=u'The real name for the site community',
                            required=False,
                            default=None)


class INoAccountCreationEmail(interface.Interface):
    """
    A marker that indicates if an account creation email should be sent
    upon a new account creation
    """
INoAccountCreationEmail.setTaggedValue('_ext_is_marker_interface', True)


import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
    "Code should not access this directly; move your tests to the mathcounts site package."
    " The only valid use is existing ZODB objects",
    "nti.app.sites.mathcounts.interfaces",
    "IMathcountsUser",
    "IMathcountsCoppaUserWithoutAgreement",
    "IMathcountsCoppaUserWithAgreement",
    "IMathcountsCoppaUserWithAgreementUpgraded",
    "IMathcountsCoppaUserWithoutAgreementUserProfile",
    "IMathcountsCoppaUserWithAgreementUserProfile")

zope.deferredimport.deprecatedFrom(
    "Code should not access this directly; move your tests to the columbia site package."
    " The only valid use is existing ZODB objects",
    "nti.app.sites.columbia.interfaces",
    "IColumbiaBusinessUserProfile")
