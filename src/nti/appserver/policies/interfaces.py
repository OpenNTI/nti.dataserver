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

    # TODO: These do not really belong here but we rely on them being on the policy in a few locations.
    DEFAULT_EMAIL_SENDER = TextLine(title=u'An optional email sender',
                                    description=u'An email address used to send emails to users'
                                                u'such as account creation, both on behalf of this'
                                                u'object as well as from other places. Optional.',
                                    required=False,
                                    default=None)

    NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME = NativeStringLine(title=u'The base template for sending '
                                                                       u'an email to a newly created user.',
                                                                 description=u'The asset spec for a template having both text and'
                                                                             u'HTML versions. If the asset spec is a bare name'
                                                                             u'like "foobar", it is assumed to be located in the'
                                                                             u'``templates`` directory in the package this object'
                                                                             u'is located in. Otherwise, it can be a complete spec'
                                                                             u'such as "the.package:other_dir/foobar"',
                                                                 default='nti.appserver:templates/new_user_created',
                                                                 required=False)

    NEW_USER_CREATED_EMAIL_SUBJECT = TextLine(title=u'The email subject for new user emails.',
                                              required=False,
                                              default=u'Welcome to ${site_name}')

    NEW_USER_CREATED_BY_ADMIN_EMAIL_TEMPLATE_BASE_NAME = \
        NativeStringLine(title=u'The base template for sending '
                               u'an email to a newly created user '
                               u'when created by an admin.',
                         default='nti.appserver:templates/new_user_created_by_admin',
                         required=False)

    NEW_USER_CREATED_BY_ADMIN_EMAIL_SUBJECT = \
        TextLine(title=u'The email subject for new user emails created '
                       u'by an admin.',
                 required=False,
                 default=u'Welcome to ${site_name}')

    NEW_USER_CREATED_BCC = TextLine(title=u'The bcc address for new user emails.',
                                    default=None,
                                    required=False)

    PASSWORD_RESET_EMAIL_TEMPLATE_BASE_NAME = NativeStringLine(title=u'The base template for password reset emails.',
                                                               default='password_reset_email')

    PASSWORD_RESET_EMAIL_SUBJECT = TextLine(title=u'The subject for password reset emails.',
                                            default=u'NextThought Password Reset',
                                            required=False)

    SUPPORT_EMAIL = TextLine(title=u'The support email.',
                             default=u'support@nextthought.com',
                             required=False)

    USERNAME_RECOVERY_EMAIL_TEMPLATE_BASE_NAME = NativeStringLine(title=u'The base template for username recovery emails.',
                                                                  default='username_recovery_email',
                                                                  required=False)

    USERNAME_RECOVERY_EMAIL_SUBJECT = TextLine(title=u'The email subject for username recovery emails.',
                                               default=u'Username Reminder',
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

    def user_created_by_admin_with_request(user, event):
        """
        Called when a user is created by an admin in the scope of an
        interactive request (after user_created).
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


class IRequireSetPassword(interface.Interface):
    """
    A marker that indicates if an account needs a password set, e.g.
    when an admin has created the account with no password
    """
IRequireSetPassword.setTaggedValue('_ext_is_marker_interface', True)


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
