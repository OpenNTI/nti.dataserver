#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,inconsistent-mro

from zope import interface


class IExternalLinkProvider(interface.Interface):
    """
    Adpter for content file exernal providers"
    """

    def link():
        """
        return the external link of a content file
        """
