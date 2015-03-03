#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions having to do with sending emails.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.common.deprecated import deprecated

from nti.mailer.interfaces import ITemplatedMailer

@deprecated()
def do_html_text_templates_exist(*args, **kwargs):
	return component.getUtility(ITemplatedMailer).do_html_text_templates_exist(*args,
																			   _level=5,
																			   **kwargs)

@deprecated()
def queue_simple_html_text_email(*args, **kwargs):
	return component.getUtility(ITemplatedMailer).queue_simple_html_text_email(*args,
																			   _level=6,
																			   **kwargs)

@deprecated()
def create_simple_html_text_email(*args, **kwargs):
	return component.getUtility(ITemplatedMailer).create_simple_html_text_email(*args,
																				_level=5,
																				**kwargs)
