import os
import re
import six
import sys
import email
import fnmatch
import traceback

import logging
logger = logging.getLogger( __name__ )

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
	
	indexfile = os.path.expanduser(indexfile)
	directory = os.path.expanduser(directory)
	
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
			except:
				logger.exception("Could not read message in file '%s'" % source)

