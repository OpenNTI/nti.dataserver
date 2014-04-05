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
from nti.utils.schema import Number

# pylint:disable=I0011,E0213,E0211

class IUserNotableData(IIterable):
	"""
	An object, typically registered as an adapter on the user,
	that can find the notable data for that user and answer
	other questions about it.

	Notable objects include:

	* Direct replies to :class:`.IThreadable` objects I created;

	* Top-level content objects (e.g., notes) directly shared to me;

	* Blog-entries shared directly to me;

	* Top-level objects created by certain people (people that are returned
		from subscription adapters to :class:`.IUserPresentationPriorityCreators`);

	* Top-level comments in blog entries I create;

	Iterating across this object iterates the notable objects that are
	safely viewable (pass permission checks) by the user.
	"""

	def __len__():
		"The length of this object is the number of notable objects that can be viewed."

	def __nonzero__():
		"The boolean value of this object is whether any notable objects exist"

	def get_notable_intids(min_created_time=None,
						   max_created_time=None):
		"""
		Return a :mod:`BTrees` integer set containing the notable intids for the user.

		:keyword min_created_time: If set to a timestamp, then only intids of objects
			created after that time (inclusive) will be returned.
		:keyword max_created_time: If set to a timestamp, then only intids of objects
			created before that time (inclusive) will be returned.
		"""

	def sort_notable_intids(notable_intids,
							field_name='createdTime',
							limit=None,
							reverse=False,
							reify=False):
		"""
		Given (a possible subset of) the intids previously identified as notable
		by this object, sort them according to `field_name` order.

		:keyword createdTime: Defaulting to `createdTime`, this is the field on which to sort.
		:keyword reify: If true, then the return value will be a list-like sequence supporting
			indexing and having a length. If `False` (the default) the return value may
			be a generator or index.
		:return: An iterable or list-like sequence containing intids.
		"""

	def iter_notable_intids(notable_intids, ignore_missing=False):
		"""
		Return an iterable over the objects represented by the intids
		previously returned and possibly sorted by this object. The iterable
		will have a length if the argument does.

		:keyword bool ignore_missing: If set to true, then intids that are no
			longer present will be ignored. Use this if the transaction
			that processes the ids is different than the transaction that
			collected them. Note that this may cause a discrepancy with the
			length.
		"""

	def is_object_notable(maybe_notable):
		"""
		Given an object, check to see if it should be considered part of the
		notable set for this user, returning a truthy-value.
		"""

	# TODO: Arguably this should be a separate interface we adapt to or extend
	lastViewed = Number(title="The timestamp the user last viewed this data",
						description="This is not set implicitly, but should be set explicitly"
						" by user action. 0 if never set.",
						required=True,
						default=0)


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
