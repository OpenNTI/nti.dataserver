#!/usr/bin/env python2.7

import os
import datetime

from pyramid.view import view_config

import nti.dictserver as dictserver

@view_config(route_name='dictionary.word', request_method='GET',
			 http_cache=datetime.timedelta(days=1) )
def lookup( request ):
	"""
	Entry point into dictionary for Pyramid applications.

	Treats the `PATH_INFO` as the term to define.
	"""

	environ = request.environ
	path = os.path.split( environ['PATH_INFO'] )[1]

	info = dictserver.WordInfo( path )
	dictserver.lookup( info )
	request.response.body = info.toXMLString()
	request.response.content_type = 'text/xml'
	request.response.status_int = 200

	return request.response

