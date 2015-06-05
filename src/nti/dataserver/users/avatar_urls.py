#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters and utilities for working with avatar URLs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import random
import urllib
import urlparse
from io import BytesIO

from zope import interface
from zope import component

from nti.common import create_gravatar_url
from nti.common import GENERATED_GRAVATAR_TYPES

from ..interfaces import IUser
from ..interfaces import IEntity
from ..interfaces import ICoppaUser

from .interfaces import IAvatarURL
from .interfaces import IBackgroundURL
from .interfaces import IAvatarChoices
from .interfaces import IFriendlyNamed
from .interfaces import IAvatarURLProvider
from .interfaces import ICompleteUserProfile
from .interfaces import IBackgroundURLProvider

@component.adapter(IEntity)
@interface.implementer(IAvatarURLProvider, IAvatarURL)
def AvatarURLFactory(entity):
	"""
	For legacy reasons, this factory first checks for the presence of an avatar URL
	"""
	# Something explicitly set, historical
	if getattr(entity, '_avatarURL', None):
		return _FixedAvatarWrapper(entity)

	return component.queryAdapter(entity, IAvatarURLProvider, name="generated")

@interface.implementer(IAvatarURLProvider, IAvatarURL)
class _FixedAvatarWrapper(object):

	def __init__(self, context):
		self.avatarURL = getattr(context, '_avatarURL')

# See also https://www.libravatar.org/
# for a FOSS Gravatar clone that supports delegation by domain.
# We may want to potentially run our own instance. It is written in Python.
# They provide pyLibravatar as a client library. The federation features
# use DNS and that library uses pyDNS which may or may not be gevent friendly,
# so that would have to be investigated

def _find_default_gravatar_type(*places):
	for place in places:
		gravatar_type = getattr(place, 'defaultGravatarType', None)
		if gravatar_type:
			return gravatar_type

def _username_as_email(username):
	"""
	For purposes of gravatar, we need to have the usernames be valid email
	addresses, or at least appear to be in a domain that we control.
	"""
	email = username
	if '@' not in email:
		email = email + '@alias.nextthought.com'
	return email

@component.adapter(IEntity)
@interface.implementer(IAvatarURLProvider, IAvatarURL)
class GravatarComputedAvatarURL(object):

	defaultGravatarType = 'identicon'

	def __init__(self, context):
		email = _username_as_email(context.username)
		from_real_email = False
		try:
			profile = ICompleteUserProfile(context, None)
		except TypeError:
			profile = None
		else:
			if profile and profile.email:
				email = profile.email
				from_real_email = True

		gravatar_type = _find_default_gravatar_type(profile, context, self)
		self.avatarURL = create_gravatar_url(email, gravatar_type, secure=True)
		if from_real_email:
			scheme, netloc, url, params, query, fragment = urlparse.urlparse(self.avatarURL)
			fragment = 'using_provided_email_address'
			self.avatarURL = urlparse.urlunparse((scheme, netloc, url, params, query, fragment))

@component.adapter(ICoppaUser)
@interface.implementer(IAvatarURLProvider, IAvatarURL)
class GravatarComputedCoppaAvatarURL(object):
	"""
	Coppa users aren't expected to have a valid email. Instead, they are
	expected to have choosen one of a few gravatar types or possibly permutations
	of usernames.
	"""

	defaultGravatarType = 'retro'

	def __init__(self, context):
		gravatar_type = _find_default_gravatar_type(context, self)
		self.avatarURL = create_gravatar_url(_username_as_email(context.username),
											 gravatar_type, secure=True)

@component.adapter(basestring)
@interface.implementer(IAvatarChoices)
class StringComputedAvatarURLChoices(object):
	"""
	Computes a set of choices based of the given string. The assumption is that
	the given string is not a valid email address and so does not
	have any registered gravatars; thus, we get the different fallbacks.
	"""
	def __init__(self, context):
		self.context = context

	def _compute_permutations(self):
		"""
		Returns an iterable across various permutations of the context of this object,
			intended to produce different gravatar choices, including the context.
		"""
		# Changing the case doesn't matter, the rules say to lower case it
		# We must always be sure it's something we control if we're going to be permuting
		# it
		email = _username_as_email(self.context)

		before, after = email.split('@', 1)
		return (email, ''.join(reversed(before)) + after,
				before + '@1' + after, before + '@2' + after,  # Use the '@' because it can never be a valid email now
				before + '@3' + after, before + '@4' + after,)

	def get_choices(self):
		choices = []
		for name in self._compute_permutations():
			for gen_type in GENERATED_GRAVATAR_TYPES:
				choices.append(create_gravatar_url(name, gen_type, secure=True))
		# Shuffle the choices so it's not obvious we're following a pattern to
		# create them. But shuffle them deterministically for the same input
		# so that we don't appear to jump around as we re-request this, which
		# would confuse the user.
		# Try not to shuffle what it /probably/ the default value out of its
		# first position, because that may often appear as the 'default' in
		# the UI, and if it doesn't make an actual selection, we'd like the final
		# to match. This is extremely fragile, depending on default values and the order
		# of GENERATED_GRAVATAR_TYPES. But it's really a UI bug
		first_choice = choices[0]
		tail = choices[1:]
		random.Random(hash(self.context)).shuffle(tail)
		tail.insert(0, first_choice)
		choices = tail
		return choices

@component.adapter(ICoppaUser)
@interface.implementer(IAvatarChoices)
class GravatarComputedCoppaAvatarURLChoices(StringComputedAvatarURLChoices):

	def __init__(self, context):
		super(GravatarComputedCoppaAvatarURLChoices, self).__init__(context.username)

@component.adapter(IEntity)
@interface.implementer(IAvatarChoices)
class EntityGravatarComputedAvatarURLChoices(object):
	"""
	Arbitrary entities just get their assigned URL.
	"""

	def __init__(self, context):
		try:
			self.avatarURL = IAvatarURL(context).avatarURL
		except KeyError:  # pragma: no cover
			# Typically POSKeyError blob not found?
			logger.exception('Could not resolve avatar URL')
			self.avatarURL = None

	def get_choices(self):
		return (self.avatarURL,) if self.avatarURL else ()

@component.adapter(IUser)
@interface.implementer(IAvatarChoices)
class GravatarComputedAvatarURLChoices(object):
	"""
	Normal users get their "real" avatar URL, plus some based on creating
	a fake email address that cannot possibly be registered.
	"""

	def __init__(self, context):
		self.avatarURL = IAvatarURL(context).avatarURL
		self.context = context

	def get_choices(self):
		fake_addr = _username_as_email(self.context.username.replace('@', '_'))
		choices = StringComputedAvatarURLChoices(fake_addr).get_choices()
		choices[0] = self.avatarURL
		return choices

# background

from PIL import Image, ImageFont, ImageDraw

TEXT_SIZE = 40
TEXT_COLORS = ( (0, 0, 0), )

BACKGROUND_SIZE = (60,50)
BACKGROUND_COLORS = ( (255, 0, 0, 0), )

def get_image_font(size=TEXT_SIZE):
	path = os.path.join(os.path.dirname(__file__), 'fonts/arial_bold.ttf')
	result = ImageFont.truetype(path, size)
	return result

def get_background_color(entity):
	username = getattr(entity,'username', entity)
	idx = hash(username) % len(BACKGROUND_COLORS)
	return BACKGROUND_COLORS[idx]

def get_text_color(entity):
	username = getattr(entity,'username', entity)
	idx = hash(username) % len(TEXT_COLORS)
	return TEXT_COLORS[idx]

def get_background_image_name(entity):
	parts = IFriendlyNamed(entity).get_searchable_realname_parts
	if not parts:
		parts = entity.username[0:2]
	else:
		parts = '%s%s' % (parts[0], parts[1] if len(parts) > 1 else u'')
	return parts
	
def get_background_image(entity, size=BACKGROUND_SIZE):
	parts = get_background_image_name(entity).upper()	
	font = get_image_font()
	tcolor = get_text_color(entity)
	bcolor = get_background_color(entity)
	img = Image.new('RGBA', size, bcolor)
	d = ImageDraw.Draw(img)
	d.text((0,0), parts, font=font, fill=tcolor)
	
	result = BytesIO()
	img.save(result, "PNG")
	result.flush()
	result.seek(0)
	return result

@interface.implementer(IBackgroundURLProvider, IBackgroundURL)
class _FixedBackgroundWrapper(object):

	def __init__(self, context):
		self.backgroundURL = getattr(context, '_backgroundURL')

@component.adapter(IEntity)
@interface.implementer(IBackgroundURLProvider, IBackgroundURL)
def BackgroundURLFactory(entity):
	if getattr(entity, '_backgroundURL', None):
		return _FixedAvatarWrapper(entity)
	return component.queryAdapter(entity, IBackgroundURLProvider, name="generated")

@component.adapter(IEntity)
@interface.implementer(IBackgroundURLProvider, IBackgroundURL)
class GeneratedBackgroundURL(object):

	def __init__(self, context):
		name = get_background_image_name(context).lower()
		name = urllib.quote("%s.png" % name)
		self.backgroundURL = "/dataserver2/backgrounds/" % name
