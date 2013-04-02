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

class ICloudSearchStoreService(search_interfaces.IRedisStoreService):
	store = schema.Object(ICloudSearchStore, title='CloudSearch store')

class ICloudSearchQueryParser(search_interfaces.ISearchQueryParser):
	pass

class ICloudSearchEntityIndexManager(search_interfaces.IEntityIndexManager):
	pass
