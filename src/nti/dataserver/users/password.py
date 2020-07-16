#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import gevent

from zope import component

from zope.password.interfaces import IPasswordManager

logger = __import__('logging').getLogger(__name__)


class Password(object):
    """
    Represents the password of a principal, as
    encoded by a password manager. Immutable.
    """

    def __init__(self, password, manager_name='bcrypt'):
        """
        Creates a password given the plain text and the name of a manager
        to encode it with.

        :key manager_name string: The name of the :class:`IPasswordManager` to use
                to manager this password. The default is ``bcrypt,`` which uses a secure,
                salted hash. This is the recommended manager. If it is not available (due to the
                absence of C extensions?) the ``pbkdf2`` manager can be used. See :mod:`z3c.bcrypt`
                and :mod:`zope.password`.
        """

        manager = component.getUtility(IPasswordManager, name=manager_name)
        self.__encoded = manager.encodePassword(password)
        self.password_manager = manager_name

    def checkPassword(self, password):
        """
        :return: Whether the given (plain text) password matches the
        encoded password stored by this object.
        """
        manager = component.getUtility(IPasswordManager,
                                       name=self.password_manager)

        # Depending on our alg, we may be entering a cpu intensive operation
        # (bcrypt). Push this to our threadpool to free up our worker.
        pool = gevent.get_hub().threadpool
        result = pool.apply(manager.checkPassword, (self.__encoded, password))
        return result

    def getPassword(self):
        """
        Like the zope pluggableauth principals, we allow getting the raw
        bytes of the password. Obviously these are somewhat valuable, even
        when encoded, so take care with them.
        """
        return self.__encoded

    # Deliberately has no __eq__ method, passwords cannot
    # be directly compared outside the context of their
    # manager.
_Password = Password  # BWC
