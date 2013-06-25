# -*- coding: utf-8 -*-
"""
Chatter commands

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import requests
import urlparse
import collections

from pyramid.threadlocal import get_current_request

from zope import interface
from zope import component

from . import SalesforceException
from . import InvalidSessionException
from . import interfaces as sf_interfaces

VERSION = u'v27.0'
TOKEN_URL = u'https://na1.salesforce.com/services/oauth2/token'

def refresh_token(client_id, refresh_token, client_secret=None):
	"""
	send a request for a new access token.
	"""
	payload = {u'client_id':client_id, 'grant_type':'refresh_token', u'refresh_token':refresh_token }
	if client_secret:
		payload['client_secret'] = client_secret
	r = requests.post(TOKEN_URL, data=payload)
	data = r.json()
	assert r.status_code == 200
	assert u'error' not in data, data.get(u'error_description', data.get(u'error'))
	return data

def is_invalid_session_id(data):
	data = data[0] if isinstance(data, collections.Sequence) and data else data
	return data and isinstance(data, collections.Mapping) and data.get('errorCode') == 'INVALID_SESSION_ID'

def check_error(data):
	data = data[0] if isinstance(data, collections.Sequence) and data else data
	if isinstance(data, collections.Mapping) and u'errorCode' in data:
		raise SalesforceException(data.get(u'errorCode'), data.get(u'message'))

def check_response(r, expected_status=None):
	data = r.json()
	if not is_invalid_session_id(data):
		check_error(data)
		if expected_status and r.status_code != expected_status:
			raise SalesforceException('invalid response status code')
	return data

def get_chatter_user(instance_url, access_token, version=VERSION):
	url = '%s/services/data/%s/chatter/users/me' % (instance_url, version)
	headers = {u'Authorization': u'Bearer %s' % access_token}
	r = requests.get(url, headers=headers)
	data = check_response(r, 200)
	return data

def poll_news_feed(instance_url, access_token, service_url=None, version=VERSION):
	if not service_url:
		url = '%s/services/data/%s/chatter/feeds/news/me/feed-items' % (instance_url, version)
	else:
		url = urlparse.urljoin(instance_url, service_url)
	headers = {u'Authorization': u'Bearer %s' % access_token}
	r = requests.get(url, headers=headers)
	data = check_response(r, 200)
	return data

def get_feed_item(instance_url, access_token, feedItemId='0D5i00000040kEUCAY', version=VERSION):
	url = '%s/services/data/%s/chatter/feed-items/%s' % (instance_url, version, feedItemId)
	headers = {u'Authorization': u'Bearer %s' % access_token}
	r = requests.get(url, headers=headers)
	data = check_response(r, 200)
	return data

def post_text_news_feed_item(instance_url, access_token, userId, text, version=VERSION):
	payload = {u'text': unicode(text)}
	url = '%s/services/data/%s/chatter/feeds/news/%s/feed-items' % (instance_url, version, userId)
	headers = {u'Authorization': u'Bearer %s' % access_token}
	r = requests.post(url, params=payload, headers=headers)
	data = check_response(r, 201)
	return data

def add_text_feed_comment(instance_url, access_token, feedItemId, text, version=VERSION):
	payload = {u'text': unicode(text)}
	url = '%s/services/data/%s/chatter/feed-items/%s' % (instance_url, version, feedItemId)
	headers = {u'Authorization': u'Bearer %s' % access_token}
	r = requests.post(url, params=payload, headers=headers)
	data = check_response(r, 201)
	return data

def get_salesforce_app(request=None):
	request = request or get_current_request()
	site_names = ('',)
	if request:  # pragma: no cover
		site_names = getattr(request, 'possible_site_names', ()) + site_names

	for name in site_names:
		util = component.queryUtility(sf_interfaces.ISalesforceApplication, name=name)
		if util is not None:
			return util
	return None

def _wrap(func, *args, **kwargs):
	def f():
		func(*args, **kwargs)
	return f

@interface.implementer(sf_interfaces.IChatter)
class Chatter(object):

	def __init__(self, response_token, userId=None, refresh_token=None):
		self._userId = userId
		self.response_token = response_token
		self.refresh_token = refresh_token or response_token.get('refresh_token')

	@property
	def application(self):
		return get_salesforce_app()

	@property
	def userId(self):
		if not self._userId:
			cuser = self.get_chatter_user()
			self._userId = unicode(cuser['id'])
		return self._userId
	
	def get_chatter_user(self):
		result = self._execute_valid_session(get_chatter_user)
		return result

	def get_feed_item(self, feedItemId):
		result = self._execute_valid_session(get_feed_item, feedItemId=feedItemId)
		return result

	def poll_news_feed(self, all_pages=False):
		result = []
		nextPageUrl = None
		while True:
			data = self._execute_valid_session(poll_news_feed, service_url=nextPageUrl)
			items = data.get('items')
			nextPageUrl = data.get('nextPageUrl')
			if items:
				result.append(data)
			if not all_pages or not nextPageUrl:
				break
		return result
	
	def post_text_news_feed_item(self, text):
		userId = self.userId
		result = self._execute_valid_session(post_text_news_feed_item, userId=userId, text=text)
		return result

	def add_text_feed_comment(self, feedItemId, text):
		result = self._execute_valid_session(add_text_feed_comment, feedItemId=feedItemId, text=text)
		return result
	
	def new_response_token(self):
		if self.refresh_token:
			application = self.application
			self.response_token = refresh_token(client_id=application.ClientID, refresh_token=self.refresh_token)
			return self.response_token
		return None

	def _execute_valid_session(self, func, **kwargs):
		rt = self.response_token
		for _ in xrange(2):
			access_token = rt.get(u'access_token')
			if not access_token:
				rt = self.new_response_token()
			result = func(instance_url=rt[u'instance_url'], access_token=rt[u'access_token'], **kwargs) if rt else None
			if is_invalid_session_id(result):
				rt = self.new_response_token()
		if is_invalid_session_id(result):
			raise InvalidSessionException()
		return result
	
