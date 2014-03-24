#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Notable data interfaces.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from dolmen.builtins.interfaces import IIterable

class IUserNotableData(IIterable):
	"""
	An object, typically registered as an adapter on the user,
	that can find the notable data for that user and answer
	other questions about it.

	Notable objects include:

	* Direct replies to :class:`.IThreadable` objects I created;

	* Top-level objects directly shared to me;

	* Top-level objects created by certain people (people that are returned
		from subscription adapters to :class:`.IUserPresentationPriorityCreators`)

	Iterating across this object iterates the notable objects that are
	safely viewable (pass permission checks) by the user.
	"""

	def __len__():
		"The length of this object is the number of notable objects that can be viewed."

	def __nonzero__():
		"The boolean value of this object is whether any notable objects exist"

	def get_notable_intids(max_created_time=None):
		"""
		Return a :mod:`BTRees` integer set containing the notable intids for the user.

		:keyword max_created_time: If set to a timestamp, then only intids of objects
			created before that time will be returned.
		"""

	def sort_notable_intids(notable_intids, field_name='createdTime', limit=None, reverse=False):
		"""
		Given (a possible subset of) the intids previously identified as notable
		by this object, sort them according to `field_name` order.

		:keyword createdTime: Defaulting to `createdTime`, this is the field on which to sort.

		"""

	# TODO: Add a method and an efficient implementation to check whether an object
	# is part of this notable set.

class IUserPresentationPriorityCreators(interface.Interface):
	"""
	Registered as a subscription adapter to a (subclass of)
	:class:`IUser` and the request, these are used to provide
	a set of the creator usernames that take priority when
	presenting data to the user.
	"""

	def iter_priority_creator_usernames():
		"""
		Iterates across the usernames of creators that have priority.
		There is no particular ordering among these creators.
		"""
