#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Temporary home for the schemas that define the preferences
for apps on the platform. (A temporary home is fine because these
are only in the ZCA, not the database---unless a ZCA site is
persisted. Ultimately expect this and the ZCML file to be moved
to zope-style products.)

The :mod:`zope.preference` package has great documentation, check
it out.

Things to remember:

* The schema interfaces can only have fields, and they should
  generally be primitive types. Never use an interface that is already
  a model object.
* The preferences are arranged in a tree, beginning with the (empty) root.
  This tree is expressed in the ZCML file in the way groups are named.
  Children of the tree have no dots in their name, sub-children have
  one dot and so on. These names are extremely important and become
  part of the URL and data and should not change.
* When to make a new child (group) versus add settings to an existing
  schema? Because children can be fetched and edited independently,
  settings that are frequently updated together (or not updated when
  other settings are) are a good candidate for a group. When parent
  data is fetched, all (recursive) children are also fetched.
* If you add a group, you must add it to the ZCML file.
* Preferences can have defaults specified in the schema. They can also
  have defaults specified on a site-by-site basis, and even at particular
  nodes in the URL tree (for example, the default sort order for
  forums might be different than for UGD).
* When defining fields, prefer the objects in :mod:`nti.utils.schema`
  over similar objects in :mod:`zope.schema` for better error messages,
  censoring support, etc.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.interface import Interface
from nti.utils import schema

from . import MessageFactory as _

class IWebAppUserSettings(Interface):
	"""
	The root of the settings tree for browser-application
	specific preferences. See comments in the ZCML file for
	naming.
	"""

	preferFlashVideo = schema.Bool(
		title=_('Prefer Flash-based video instead of native HTML video when possible'),
		default=False)


class IChatPresenceSettings(Interface):
	"""
	A child of the root, specifying chat presence defaults.
	"""
