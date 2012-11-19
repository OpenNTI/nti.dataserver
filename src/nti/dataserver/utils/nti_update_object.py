#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import six
import argparse
import anyjson as json
from pprint import pprint

from zope import component

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
	
def get_ntiid(arg):
	try:
		oid = int( arg, 0 )
		ntiid = ntiids.make_ntiid( type=ntiids.TYPE_OID, specific=oid )
	except ValueError:
		ntiid = arg
		ntiids.validate_ntiid_string( ntiid )
	return ntiid

def get_external_object(json_exp=None, json_file=None, fields=()):
	result = {}
	
	# process json in args
	if json_exp:
		d = json.loads(unicode(json_exp))
		result.update(d)
	
	# process an json input file
	if json_file:
		path = os.path.expanduser(json_file)
		with open(path, "rU") as f:
			d = json.loads(unicode(f.read()))
		result.update(d)

	# process any key/value pairs
	for f in fields or ():
		p = f.split('=')
		if p and len(p) >=2:
			result[unicode(p[0])] = unicode(p[1])
	
	for k in result.keys():
		if k in forbidden_fields:
			raise Exception('Cannot set prohibited key "%s"' % k)
	return result

def find_object(ntiid):
	obj = ntiids.find_object_with_ntiid(ntiid)
	if obj is None:
		raise Exception("Cannot find object with NTIID '%s'" % ntiid)
	elif not nti_interfaces.IModeledContent.providedBy(obj):
		raise Exception("Object referenced by '%s' does not implement IModeledContent interface" % ntiid)
	return obj

def get_creator(obj):
	result = obj.creator
	if isinstance(result, six.string_types):
		result = users.Entity.get_entity(result)
	return result
	
def read_source(obj, ext_object):
	result = to_external_object(obj)
	for n in forbidden_fields:
		result.pop(n, None)
	result.update(ext_object)
	return result

def update_object(creator, obj, ext_object, verbose=False):
	# make sure we preseve the IThreadable fields
	if nti_interfaces.IThreadable.providedBy(obj):
		ext_object = read_source(obj, ext_object)
		
	objId = obj.id
	containerId = obj.containerId
	with creator.updates():
		obj = creator.getContainedObject( containerId, objId )
		obj = update_from_external_object(obj, ext_object)
		if verbose:
			pprint(to_external_object(obj))
	return obj

def get_cascadable_properties(obj, ext_obj, cascade=False):
	result = {}
	if cascade and nti_interfaces.IThreadable.providedBy(obj):
		ip = getattr(obj, "_inheritable_properties_", ())
		for n in ip:
			if n in ext_obj:
				result[n] = ext_obj[n]
	return result

def reference_object(master, slave):
	result = slave.inReplyTo == master
	if not result:
		for r in slave.references or ():
			result = r == master
			if result: break
	return result

def process_cascade(modeled_obj, ext_obj, verbose=False):
	containerId = modeled_obj.containerId
	dataserver = component.getUtility( nti_interfaces.IDataserver)
	users_folder = nti_interfaces.IShardLayout( dataserver ).users_folder
	for user in users_folder.values():
		container = user.getContainer(containerId, {}) if hasattr(user, 'getContainer') else {}
		for obj in container.values():
			if reference_object(modeled_obj, obj):
				update_object(user, obj, ext_obj, verbose)
				#TODO: Do we recurse?
			
def process_update(oid, json_exp=None, json_file=None, fields=(), cascade=False, verbose=False):
	ntiid = get_ntiid(oid)
	modeled_obj = find_object(ntiid)
	ext_obj = get_external_object(json_exp, json_file, fields)
	creator = get_creator(modeled_obj)
	modeled_obj = update_object(creator, modeled_obj, ext_obj, verbose)
	casc_properties = get_cascadable_properties(modeled_obj, ext_obj, cascade)
	if casc_properties:
		process_cascade(modeled_obj, casc_properties, verbose)
	return modeled_obj

def _process_args(args):
	process_update(args.id, args.json, args.input, args.fields, args.cascade, args.verbose)

def main():
	arg_parser = _create_args_parser()
	args = arg_parser.parse_args()
	run_with_dataserver( environment_dir=args.env_dir, function=lambda: _process_args(args) )

if __name__ == '__main__':
	main()