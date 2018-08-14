#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope.interface.common.mapping import IEnumerableMapping


class IContextLastSeenContainer(IEnumerableMapping):
    """
    Something that is an unordered bag of context ntiid and
    the last timestamp they were visited (seen)
    """

    def append(item, timestamp=None):
        """
        Add an item to this container
        """

    def extend(items, timestamp=None):
        """
        Add the specified items to this container
        """

    def contexts():
        """
        return an iterable with all context ntiids in this container
        """

    def pop(k, default):
        """
        remove specified key and return the corresponding value
        """
