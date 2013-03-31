# -*- coding: utf-8 -*-
"""
CloundSearch interfaces.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

from zope import schema
from zope import interface

from dolmen.builtins import IDict

from . import interfaces as search_interfaces

from nti.utils import schema as nti_schema

class IRedisStoreService(interface.Interface):

	queue_name = nti_schema.ValidTextLine(title="Queue name", required=True)
	sleep_wait_time = nti_schema.Number(title="Message interval", required=True)
	expiration_time = nti_schema.Number(title="Message redis expiration time", required=True)

	def add(docid, username):
		"""
		register an add index operation with redis

		:param docid document id
		:param username target user
		"""

	def update(docid, username):
		"""
		register a update index operation with redis

		:param docid document id
		:param username target user
		"""

	def delete(docid, username):
		"""
		register a delete index operation with redis

		:param docid document id
		:param username target user
		"""

	def process_messages(msgs):
		"""
		process the messages read from redis
		"""

# cloud search

class ICloudSearchObject(IDict):
	pass

class ICloudSearchStore(interface.Interface):

	def get_domain(domain_name=None):
		"""
		Return the domain with the specified name
		"""

	def get_document_service(domain_name=None):
		"""
		Return a document service for the specified domain
		"""

	def get_search_service(domain_name=None):
		"""
		Return the searchh service for the specified domain
		"""

	def get_aws_domains():
		"""
		Return all aws search domains
		"""

	def search(*args, **kwargs):
		"""
		Perform a CloudSearch search
		"""

	def add(docid, username, service=None, commit=True):
		"""
		Index the specified document in CloudSearch
		"""

	def delete(docid, username, ommit=True):
		"""
		Delete the specified document from CloudSearch
		"""

	def handle_cs_errors(errors):
		"""
		Handle the specififed CloudSearch error meessages
		"""

class ICloudSearchStoreService(IRedisStoreService):
	store = schema.Object(ICloudSearchStore, title='CloudSearch store')

class ICloudSearchQueryParser(search_interfaces.ISearchQueryParser):
	pass

class ICloudSearchEntityIndexManager(search_interfaces.IEntityIndexManager):
	pass
