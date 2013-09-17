#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Makes sure we can externalize Zope Preference
objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import none
from hamcrest import has_entries

import nti.tests

from zope.preference import preference
from zope.preference.interfaces import IPreferenceGroup
from zope.component import provideUtility

# First, define a basic preference schema
import zope.interface
import zope.schema
class IZMIUserSettings(zope.interface.Interface):
	"""Basic User Preferences"""
	# The root

	email = zope.schema.TextLine(
		title=u"E-mail Address",
		description=u"E-mail Address used to send notifications")

	skin = zope.schema.Choice(
		title=u"Skin",
		description=u"The skin that should be used for the ZMI.",
		values=['Rotterdam', 'ZopeTop', 'Basic'],
		default='Rotterdam')

	showZopeLogo = zope.schema.Bool(
		title=u"Show Zope Logo",
		description=u"Specifies whether Zope logo should be displayed "
				u"at the top of the screen.",
		default=True)

class IFolderSettings(zope.interface.Interface):
	"""Basic User Preferences"""
	# A child

	shownFields = zope.schema.Set(
		title=u"Shown Fields",
		description=u"Fields shown in the table.",
		value_type=zope.schema.Choice(['name', 'size', 'creator']),
		default=set(['name', 'size']))

	sortedBy = zope.schema.Choice(
		title=u"Sorted By",
		description=u"Data field to sort by.",
		values=['name', 'size', 'creator'],
		default='name')

from . import ConfiguringTestBase
from . import externalizes

from zope.security.interfaces import NoInteraction
import zope.security.management
from zope.annotation.interfaces import IAttributeAnnotatable
from zope import interface

class TestExternalizePreferences(ConfiguringTestBase):

	# The principal in the interaction must be annotatable
	@interface.implementer(IAttributeAnnotatable)
	class Principal(object):
		id = 'zope.user'

	class Participation(object):
		interaction = None
		def __init__(self,p):
			self.principal = p


	def setUp(self):
		super(TestExternalizePreferences,self).setUp()
		self.settings = preference.PreferenceGroup(
			"ZMISettings",
			schema=IZMIUserSettings,
			title="ZMI User Settings",
			description='' )
		self.folder_settings = preference.PreferenceGroup(
			'ZMISettings.Folder', # Hierarchy matters! Must match utility names (happens automatically from ZCML)
			schema=IFolderSettings,
			title="Folder Content View Settings" )

	def test_no_interaction_fails(self):
		# Without an interaction, they cannot be read.
		# Without extra special work, prefs are always
		# for the current user
		try:
			assert_that( self.settings, externalizes() )
			self.fail()
		except NoInteraction:
			pass

	def test_externalize_prefs(self):
		settings = self.settings


		participation = self.Participation(self.Principal())
		zope.security.management.newInteraction(participation)

		# Now it can work
		assert_that( settings, externalizes() )

		# And when it does, all the defaults are taken into account
		assert_that( settings,
					 externalizes( has_entries( 'email', none(),
												'showZopeLogo', True,
												'skin', 'Rotterdam',
												'Class', 'Preference_ZMISettings',
												'MimeType', 'application/vnd.nextthought.preference.zmisettings') ) )


	def test_externalize_sub_prefs(self):
		# When we start with a root object,
		# and there are sub-objects in ZCA,
		# we get those as well


		participation = self.Participation(self.Principal())
		zope.security.management.newInteraction(participation)

		provideUtility( self.settings, IPreferenceGroup, name=self.settings.__id__ )
		provideUtility( self.folder_settings, IPreferenceGroup, name=self.folder_settings.__id__ )

		assert_that( self.settings,
					 externalizes( has_entries(
						 'Folder', has_entries(
							 'Class', 'Preference_ZMISettings_Folder',
							 'MimeType', 'application/vnd.nextthought.preference.zmisettings.folder') ) ) )
