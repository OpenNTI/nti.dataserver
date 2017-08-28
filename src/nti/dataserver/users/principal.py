#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import warnings

from zope import component

from zope.cachedescriptors.property import cachedIn

from z3c.password.interfaces import IPasswordUtility

from nti.dataserver.sharing import SharingSourceMixin

from nti.dataserver.users.entity import Entity
from nti.dataserver.users.entity import named_entity_ntiid

from nti.dataserver.users.interfaces import _VERBOTEN_PASSWORDS
from nti.dataserver.users.interfaces import InsecurePasswordIsForbidden
from nti.dataserver.users.interfaces import PasswordCannotConsistOfOnlyWhitespace

from nti.dataserver.users.password import Password as _Password


class Principal(SharingSourceMixin, Entity):  # order matters
    """ 
    A Principal represents a set of credentials that has access to the system.

    .. py:attribute:: username

            The username.
    .. py:attribute:: password

            A password object. Not comparable, only supports a `checkPassword` operation.
    """

    # TODO: Continue migrating this towards zope.security.principal, the zope principalfolder
    # concept.
    password_manager_name = 'bcrypt'

    def __init__(self,
                 username=None,
                 password=None,
                 parent=None):

        super(Principal, self).__init__(username, parent=parent)
        if password:
            self.password = password

    def has_password(self):
        return bool(self.password)

    def _get_password(self):
        return self.__dict__.get('password', None)

    def _set_password(self, np):
        # TODO: Names for these?
        component.getUtility(IPasswordUtility).verify(np)
        # NOTE: The password policy objects do not have an option to forbid
        # all whitespace, so we implement that manually here.
        # TODO: Subclass the policy and implement one that does, install that
        # and migrate
        if np and not np.strip():  # but do allow leading/trailing whitespace
            raise PasswordCannotConsistOfOnlyWhitespace()
        # NOTE: The password policy objects do not have an option to forbid
        # specific passwords from a list, so we implement that manually here.
        # TODO: Subclass the policy and implement one that does, as per above
        if np and np.strip().upper() in _VERBOTEN_PASSWORDS:
            raise InsecurePasswordIsForbidden(np)

        self.__dict__['password'] = _Password(np, self.password_manager_name)
        # otherwise, no change

    def _del_password(self):
        del self.__dict__['password']
    password = property(_get_password, _set_password, _del_password)

    NTIID_TYPE = None
    NTIID = cachedIn('_v_ntiid')(named_entity_ntiid)


if os.getenv('DATASERVER_TESTING_PLAIN_TEXT_PWDS') == 'True':
    # For use by nti_run_integration_tests, nti_run_general_purpose_tests;
    # plain text passwords are much faster than bcrpyt, and since
    # the tests use HTTP Basic Auth, this makes a difference
    warnings.warn("WARN: Configuring with plain text passwords")
    Principal.password_manager_name = 'Plain Text'
