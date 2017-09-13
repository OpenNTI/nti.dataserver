#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration between pyramid and capabilities.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# TODO: There are two main ways to integrate this into pyramid's view
# security. It could either be a 'custom predicate' or an extension
# to the authorization policy.

# If it is a custom predicate, then the view/route it is
# applied to will not be considered for a match if the capability
# is not present. If that was the only possibility, then the user will
# get a 404 (but a 403 would be more appropriate). On the plus side,
# it would allow registering views at the same context/route/name
# just doing different things based on what capabilities you have.

# An authorization policy would extend the normal ACL policy,
# and allow the 'permission' keyword argument to accept a sequence
# of things, one IPermission and one ICapability. This has exactly the
# opposite characteristics: it's not a predicate, so it is only checked
# after a particular view has been picked.

# Either way, we need to efficiently check for the presence of
# the capability (through binding the authenticated user to produce a vocabulary,
# probably).
