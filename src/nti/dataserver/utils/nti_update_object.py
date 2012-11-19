#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import six
import argparse
import anyjson as json
from pprint import pprint

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.ntiids import ntiids

import logging
logger = logging.getLogger( __name__ )

forbidden_fields = set([v for k,v in ext_interfaces.StandardExternalFields.__dict__.iteritems() if not k.startswith( '_' ) and k !='ALL'])
forbidden_int_fields = set([v for k,v in ext_interfaces.StandardInternalFields.__dict__.iteritems() if not k.startswith( '_' )])
forbidden_fields = tuple(forbidden_fields.union(forbidden_int_fields)) + ('flattenedSharingTargetNames', 'sharedWith', 'body')

def _create_args_parser():
	arg_parser = argparse.ArgumentParser( description="Set object attributes." )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'id', help="Object's OID or NTIID" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')		
	arg_parser.add_argument( '-j', '--json', dest='json', help="JSON expression" )
	arg_parser.add_argument( '-i', '--input', dest='input', help="JSON input file" )
	arg_parser.add_argument( '-f', '--fields', dest='fields', nargs="*", help="Key=value pairs" )
	arg_parser.add_argument( '--cascade', help="Cascade operation on threadable objects", action='store_true', dest='cascade')	
	return arg_parser
	
def _get_ntiid(arg):
	try:
		oid = int( arg, 0 )
		ntiid = ntiids.make_ntiid( type=ntiids.TYPE_OID, specific=oid )
	except ValueError:
		ntiid = arg
		ntiids.validate_ntiid_string( ntiid )
	return ntiid

def _find_object(ntiid):
	obj = ntiids.find_object_with_ntiid(ntiid)
	if obj is None:
		raise Exception("Cannot find object with NTIID '%s'" % ntiid)
	elif not nti_interfaces.IModeledContent.providedBy(obj):
		raise Exception("Object referenced by '%s' does not implement IModeledContent interface" % ntiid)
	return obj

def _get_external_object(args):
	result = {}
	
	# process ant json in args
	if args.json:
		d = json.loads(unicode(args.json))
		result.update(d)
	
	# process an json input file
	if args.input:
		path = os.path.expanduser(args.input)
		with open(path, "rU") as f:
			d = json.loads(unicode(f.read()))
		result.update(d)

	# process any key/value pairs
	for f in args.fields or ():
		p = f.split('=')
		if p and len(p) >=2:
			result[unicode(p[0])] = unicode(p[1])
	
	for k in result.keys():
		if k in forbidden_fields:
			raise Exception('Cannot set prohibited key "%s"' % k)
	return result

def _get_creator(obj):
	result = getattr(obj, ext_interfaces.StandardInternalFields.CREATOR)
	if isinstance(result, six.string_types):
		result = users.Entity.get_entity(result)
	return result
	
def _update_object(creator, obj, ext_object, verbose=False):
	objId = obj.id
	containerId = obj.containerId
	with creator.updates():
		obj = creator.getContainedObject( containerId, objId )
		obj = update_from_external_object(obj, ext_object)
		if verbose:
			pprint(to_external_object(obj))

def _process(args):
	ntiid = _get_ntiid(args.id)
	modeled_obj = _find_object(ntiid)
	ext_obj = _get_external_object(args)
	creator = _get_creator(modeled_obj)
	modeled_obj = _update_object(creator, modeled_obj, ext_obj, args.verbose)
	return modeled_obj

def main():
	arg_parser = _create_args_parser()
	args = arg_parser.parse_args()
	run_with_dataserver( environment_dir=args.env_dir, function=lambda: _process(args) )

if __name__ == '__main__':
	main()