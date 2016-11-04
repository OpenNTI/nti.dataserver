#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Capability support.

Capabilities are similar to :class:`zope.security.interfaces.IPermission`, but the
difference is that they are higher level; they are umbrellas, if you will. A permission
is applied to one particular object in an ACL and enforced individually by views,
but a capability protects an entire feature (which may make up several views and multiple different
objects).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
