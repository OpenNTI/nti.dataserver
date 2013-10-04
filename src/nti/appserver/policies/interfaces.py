# -*- coding: utf-8 -*-
"""
Site policies interfaces

$Id: interfaces.py 19763 2013-05-31 22:02:07Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface


class ISitePolicyUserEventListener(interface.Interface):
    """
    Register instances of these as utilities by the name of the site
    they should apply to.
    """

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

    # TODO : I'm not entirely sure this belongs here. Might want to rethink this a lot
    def upgrade_user(user):
        """
        Transition a user from a limited form to the next lest limited forrm.
        Specifically intended to deal with providing coppa consent.
        """

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
	"IColumbiaBusinessUserProfile" )
