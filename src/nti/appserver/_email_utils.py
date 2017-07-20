#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions having to do with sending emails.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.base.deprecation import deprecated

from nti.mailer.interfaces import ITemplatedMailer


def mailer():
    return component.getUtility(ITemplatedMailer)


@deprecated()
def do_html_text_templates_exist(*args, **kwargs):
    return mailer().do_html_text_templates_exist(*args, _level=5, **kwargs)


@deprecated()
def queue_simple_html_text_email(*args, **kwargs):
    return mailer().queue_simple_html_text_email(*args, _level=6, **kwargs)


@deprecated()
def create_simple_html_text_email(*args, **kwargs):
    return mailer().create_simple_html_text_email(*args, _level=5, **kwargs)
