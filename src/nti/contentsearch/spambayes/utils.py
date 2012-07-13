from __future__ import print_function, unicode_literals

import os
import re
import six
import sys
import email
import binascii
import fnmatch
import traceback
import collections
import transaction

from logging import DEBUG
from email.message import Message as eMessage

from nti.contentsearch.spambayes.tokenizer import tokenize
from nti.contentsearch.spambayes.storage import SQL3Classifier

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

def _textparts(msg):
	"""Return a set of all msg parts with content maintype 'text'."""
	return set(filter(lambda part: part.get_content_maintype() == 'text', msg.walk()))

header_break_re = re.compile(r"\r?\n(\r?\n)")

def _extract_message_headers(text):
	m = header_break_re.search(text)
	if m:
		eol = m.start(1)
		text = text[:eol]
	if ':' not in text:
		text = ""

	return text

base64_re = re.compile(r"""
    [ \t]*
    [a-zA-Z0-9+/]*
    (=*)
    [ \t]*
    \r?
    \n
""", re.VERBOSE)

def _repair_damaged_base64(text):
	i = 0
	while True:
		# text[:i] looks like base64.  Does the line starting at i also?
		m = base64_re.match(text, i)
		if not m:
			break
		i = m.end()
		if m.group(1):
			# this line has a trailing '=' -- the base64 part is done.
			break
	base64text = ''
	if i:
		base64 = text[:i]
		try:
			base64text = binascii.a2b_base64(base64)
		except:
			# there's no point in tokenizing raw base64 gibberish.
			pass
	return base64text + text[i:]

# -----------------------------------

def get_email_message(obj):
	"""Return an email Message object. """

	if isinstance(obj, email.Message.Message):
		return obj
	
	if hasattr(obj, "read"):
		obj = obj.read()
	try:
		msg = email.message_from_string(obj)
	except email.Errors.MessageParseError:
		# Wrap the raw text in a bare Message object.  Since the
		# headers are most likely damaged, we can't use the email
		# package to parse them, so just get rid of them first.
		headers = _extract_message_headers(obj)
		obj = obj[len(headers):]
		msg = email.Message.Message()
		msg.set_payload(obj)
	return msg

def get_email_message_as_string(msg, unixfrom=False):
	"""Convert a Message object to a string"""

	if isinstance(msg, six.string_types):
		return msg
	else:
		try:
			return msg.as_string(unixfrom)
		except TypeError:
			ty, val, tb = sys.exc_info()
			exclines = traceback.format_exception(ty, val, tb)[1:]
			excstr = "    ".join(exclines).strip()
			
			headers = []
			if unixfrom:
				headers.append(msg.get_unixfrom())
			for (hdr, val) in msg.items():
				headers.append("%s: %s" % (hdr, val))
			
			headers.append("X-DS-Exception: %s" % excstr)
			parts = ["%s\n" % "\n".join(headers)]
			boundary = msg.get_boundary()
			for part in msg.get_payload():
				if boundary:
					parts.append(boundary)
				try:
					parts.append(part.as_string())
				except AttributeError:
					parts.append(str(part))
			if boundary:
				parts.append("--%s--" % boundary)
			# make sure it ends with a newline:
			return "\n".join(parts)+"\n"

def get_email_messages(directory, fnfilter='*', indexfile=None, default_spam=True, separator=None):
	
	directory = os.path.expanduser(directory)
	indexfile = os.path.expanduser(indexfile) if indexfile else indexfile
		
	index = {}
	if indexfile and os.path.exists(indexfile):
		with open(indexfile, "r") as fp:
			for line in fp:
				line = line.rstrip('\n\r')
				data = line.split(separator)
				if len(data) >=2:
					is_spam = data[0].lower() == 'spam'
					fname = os.path.basename(data[1])
					index[fname] = is_spam 
			
	for filename in os.listdir(directory):
		if fnmatch.fnmatch(filename, fnfilter):
			source = os.path.join(directory, filename)
			try:
				with open(source, "r") as fp:
					msg = get_email_message(fp)
					is_spam = index.get(filename, default_spam)
					yield msg, is_spam, source
			except Exception, e:
				if logger.isEnabledFor(DEBUG):
					logger.exception("Could not read message in file '%s'" % source)
				else:
					logger.error("Could not read message in file '%s'. %s" % (source, e))

# -----------------------------------

def _get_email_message_text_parts(obj):
	result = []
	if isinstance(obj, six.string_types):
		result.append(obj)
	elif isinstance(obj, eMessage):
		for part in _textparts(obj):
			try:
				text = part.get_payload(decode=True)
			except:
				text = part.get_payload(decode=False)
				text = _repair_damaged_base64(text) if text is not None else None
				
			if text:
				result.append(text)
	elif isinstance(obj, collections.Iterable):
		for m in obj:
			result.extend(_get_email_message_text_parts(m))
	elif obj:
		result.append(repr(obj))
	return result
	
def create_sql3classifier_db(dbpath, directory, include_ham=False, fnfilter='*', indexfile=None,
							default_spam=True, separator=None, batch_size=1000, *args, **kwargs):
	count = 0
	total = 0
	dbpath = os.path.expanduser(dbpath)
	sql3 = SQL3Classifier(dbpath, *args, **kwargs)

	for msg, is_spam, _ in get_email_messages(directory, fnfilter, indexfile, default_spam, separator):
		
		if not include_ham and not is_spam:
			continue
			
		for text in _get_email_message_text_parts(msg):
			sql3.learn(tokenize(text), is_spam)
			total = total + 1
			count = count + 1
			
			if count == 1:
				transaction.begin()
			elif count >= batch_size:
				transaction.commit()
				count = 0
	if count:
		transaction.commit()
	
	logger.info("%s messages(s) processed" % total)
	
	return sql3
