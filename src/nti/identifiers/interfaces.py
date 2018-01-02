#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope import interface

from zope.container.interfaces import IContainer

from nti.schema.field import ValidTextLine


class IUserExternalIdentityContainer(IContainer):
    """
    A case-insensitive container of one-to-one mappings from external_type to
    external_id for a user.
    """

    site_name = ValidTextLine(title=u"The external identity site name",
                              description=u"A user can only have an external identity tied to one site",
                              required=False)

    def add_external_mapping(external_type, external_id):
        """
        Add a mapping for this user; the external_type is the classifier
        defined by the external id holder.

        :raises MultipleUserExternalIdentitySitesError if a user is already
        mapped to another site.
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


class ExternalIdentityError(Exception):
    """
    A general error when updating a user's external identity.
    """


class MultipleUserExternalIdentitySitesError(ExternalIdentityError):
    """
    Occurs when a user may have external identities mapped across multiple
    sites.
    """
