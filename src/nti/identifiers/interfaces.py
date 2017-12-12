#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.container.interfaces import IContainer

logger = __import__('logging').getLogger(__name__)
# pylint: disable=inherit-non-class


class IUserExternalIdentityContainer(IContainer):
    """
    A case-insensitive container of one-to-one mappings from external_type to
    external_id for a user.
    """

    def add_external_mapping(external_type, external_id):
        """
        Add a mapping for this user; the external_type is the classifier
        defined by the external id holder.
        """


class IUserExternalIdentityValidator(interface.Interface):
    """
    Validates a user has the external_type/external_id mapping.
    """

    def is_valid(external_type, external_id):
        """
        Returns a bool on whether this user has this
        external_type/external_id mapping.
        """
