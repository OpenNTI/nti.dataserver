#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support error handling, especially during object IO.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import collections
import simplejson as json

from zope.interface import Invalid

from zope.container.interfaces import InvalidItemType
from zope.container.interfaces import InvalidContainerType

from zope.i18n import translate

from zope.schema.interfaces import RequiredMissing
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import ConstraintNotSatisfied

from z3c.password.interfaces import InvalidPassword

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

from nti.app.externalization import MessageFactory as _

def _json_error_map(o):
	if isinstance(o, set):
		return list(o)
	return unicode(o)

def raise_json_error(request,
					 factory,
					 v,
					 tb):
	"""
	Attempts to raise an error during processing of a pyramid request.
	We expect the client to specify that they want JSON errors.

	:param v: The detail message. Can be a string or a dictionary. A dictionary
		may contain the keys `field`, `message` and `code`.
	:param factory: The factory (class) to produce an HTTP exception.
	:param tb: The traceback from `sys.exc_info`.
	"""
	# logger.exception( "Failed to create user; returning expected error" )
	mts = (b'application/json', b'text/plain')
	accept_type = b'application/json'
	if getattr(request, 'accept', None):
		accept_type = request.accept.best_match(mts)

	if isinstance(v, collections.Mapping) and v.get('field') == 'username':
		# Our internal schema field is username, but that maps to Username on the outside
		v['field'] = 'Username'

	if isinstance(v, collections.Mapping):
		# Make sure to translate our message, if we have one.
		v['message'] = message = translate(v.get('message'), context=request)
	else:
		v = message = translate(v, context=request)

	if accept_type == b'application/json':
		try:
			v = json.dumps(v, ensure_ascii=False, default=_json_error_map)
		except TypeError:
			v = json.dumps({'UnrepresentableError': unicode(v) })
	else:
		v = unicode(v)

	result = factory(message)
	result.text = v
	result.content_type = accept_type
	raise result, None, tb

def _validation_error_to_dict(request, validation_error):
	__traceback_info__ = type(validation_error), validation_error
	# Validation error may be many things, including invalid password by the policy (see above)
	# Some places try hard to set a good message, some don't.
	msg = ''
	value = None
	declared = None
	field_name = None
	field = getattr(validation_error, 'field', None)

	if field:
		# handle FieldPropertyStoredThroughField via FieldValidationMixin
		fixed_field_name = getattr(field, '__fixup_name__', None)
		field_name = fixed_field_name or getattr(field, '__name__', field)
		declared = getattr(getattr(field, 'interface', None), '__name__', None)

	if len(validation_error.args) == 3:
		# message, field, value
		field_name = field_name or validation_error.args[1]
		msg = validation_error.args[0]
		value = validation_error.args[2]

	if not field_name and isinstance(validation_error, InvalidPassword):
		field_name = 'password'

	if 	not field_name \
		and isinstance(validation_error, RequiredMissing) \
		and validation_error.args:
		field_name = validation_error.args[0]

	if 	not field_name \
		and isinstance(validation_error, ConstraintNotSatisfied) \
		and validation_error.args:
		args = validation_error.args[0]
		value = args[0]
		field_name = args[1] if len(args) > 1 else None

	if not value:
		value = getattr(validation_error, 'value', value)

	# z3c.password and similar (nti.dataserver.users._InvalidData) set this for internationalization
	# purposes
	if getattr(validation_error, 'i18n_message', None):
		msg = translate(validation_error.i18n_message, context=request)
	else:
		if validation_error.args:
			msg = (validation_error.args[0] \
				  if not isinstance(validation_error.args[0], list) else '') or msg
		try:
			msg = translate(msg, context=request)
		except (UnicodeError, KeyError):
			# We get UnicodeDecodeError when giving a byte-string to translate that contains
			# non-ASCII (platform) characters. Since the msg can come from arbitrary user data,
			# this is a fairly easy situation to get into
			if isinstance(msg, bytes):
				try:
					msg = msg.encode('utf-8')
				except UnicodeError:
					msg = ''

	result = {'message': msg,
			  'code': validation_error.__class__.__name__,
			  'value': value,
			  'declared': declared}
	if field_name:
		result['field'] = field_name

	if getattr(validation_error, 'errors', None):
		# see schema._field._validate_sequence
		# TODO: Now this may be revealing too much info
		contained_errors = []
		try:
			for error in validation_error.errors:
				contained_errors.append(_validation_error_to_dict(request, error))
		except (KeyError, ValueError, TypeError):
			pass
		if contained_errors:
			result['suberrors'] = contained_errors

	return result

def _no_request_validation_error():
	logger.exception("Failed to update content object, bad input")
	exc_info = sys.exc_info()
	raise hexc.HTTPUnprocessableEntity, exc_info[1], exc_info[2]

def handle_validation_error(request, validation_error):
	"""
	Handles a :class:`zope.schema.interfaces.ValidationError` within
	the context of a Pyramid request by raising an
	:class:`pyramid.httpexceptions.HTTPUnprocessableEntity` error.
	Call from within the scope of a ``except`` block.

	This function never returns, it raises an exception.

	:param validation_error: The validation error being processed.
	"""
	__traceback_info__ = type(validation_error), validation_error
	# Validation error may be many things, including invalid password by the policy (see above)
	# Some places try hard to set a good message, some don't.
	exc_info = sys.exc_info()

	validation_dict = _validation_error_to_dict(request, validation_error)
	if not validation_dict.get('field'):
		# Hmm. This will be mighty confusing on the other end. Maybe we can shed some
		# light on it with our tracebacks
		logger.exception("Validation error without a field")

	raise_json_error(request,
					 hexc.HTTPUnprocessableEntity,
					 validation_dict,
					 exc_info[2])

def handle_possible_validation_error(request, e):
	if request is None:
		request = get_current_request()

	if isinstance(e, ValidationError):
		if request is None:
			_no_request_validation_error()
		else:
			handle_validation_error(request, e)
	elif isinstance(e, AssertionError):  # pragma: no cover
		# Triggered a failed assertion on our side.
		# That's bad. We probably want this to come up as a 500
		# so we log it and deal with it
		raise
	elif isinstance(e, (InvalidContainerType, InvalidItemType)):
		if request is None:
			_no_request_validation_error()

		if getattr(e, 'field', None) is None:
			e.field = 'ContainerId'
		# if getattr( e, 'value', None ) is None and len(e.args) == 2:
		# 	e.value = str(e.args[1])
		if getattr(e, 'i18n_message', None) is None:
			e.i18n_message = _("You cannot store that type of object here.")
		handle_validation_error(request, e)
	elif isinstance(e, (ValueError, Invalid, TypeError, KeyError)):  # pragma: no cover
		# These are all 'validation' errors. Raise them as unprocessable entities
		# interface.Invalid, in particular, is the root class of zope.schema.ValidationError
		_no_request_validation_error()
	else:
		raise
