#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse
from pprint import pprint

from zope import schema
from zope import interface

from nti.chatserver import interfaces as chat_interfaces

from nti.contentfragments import schema as frg_schema

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.utils.schema import find_most_derived_interface
from nti.dataserver.users import interfaces as user_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

known_imodeled = (nti_interfaces.INote, nti_interfaces.IHighlight, nti_interfaces.IRedaction, nti_interfaces.ICanvas, 
				  chat_interfaces.IMessageInfo)

forbidden_fields = set([v for k,v in ext_interfaces.StandardExternalFields.__dict__.iteritems() if not k.startswith( '_' ) and k !='ALL'])
forbidden_int_fields = set([v for k,v in ext_interfaces.StandardInternalFields.__dict__.iteritems() if not k.startswith( '_' )])
forbidden_fields = tuple(forbidden_fields.union(forbidden_int_fields)) + ('flattenedSharingTargetNames', 'sharedWith')

threadable_fields = {'inReplyTo' : frg_schema.TextUnicodeContentFragment(title="The object to which this object is directly a reply"),
					 'references': schema.List( value_type=frg_schema.TextUnicodeContentFragment(title="a reference id"),
												title="A sequence of ids this object transiently references.")}

def get_schema_fields(iface, attributes):		
	names = iface.names()
	fields = schema.getFields(iface) or {}
	for name in names or ():
		sch_def = fields.get(name, None)
		if sch_def and name not in attributes and name not in forbidden_fields and \
		   not name.startswith( '_' ) and not name[0].isupper():
			attributes[name] = sch_def
	
	for base in iface.getBases() or ():
		get_schema_fields(base, attributes)
			
def get_imodeled_schemas():
	result = {}
	all_fields = {}
	for iface in known_imodeled:
		attributes = {}
		if nti_interfaces.IThreadable in iface.getBases():
			attributes.update(threadable_fields)
		get_schema_fields(iface, attributes)
		all_fields.update(attributes)
		result[iface] = attributes
	return result, all_fields

def _create_args_parser():
	
	# parse model content schemas
	imodeled_schemas, all_fields = get_imodeled_schemas()
		
	arg_parser = argparse.ArgumentParser( description="Set object attributes." )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( '--cascade', help="Cascade operation on threadable objects", action='store_true', dest='cascade')
	
	# add params
	group = arg_parser.add_mutually_exclusive_group()
	group.add_argument('-nid', '--ntiid', dest='ntiid', help="Object NTIID" )
	group.add_argument('-oid', '--oid', dest='oid', help="Object ID (hex)")

	for name, sch in all_fields.items():
		help_ = sch.getDoc() or sch.title
		help_ = help_.replace('\n', '.')
		opt = '--%s' % name
		arg_parser.add_argument( opt, help=help_, dest=name, required=False)
			
	arg_parser.add_argument( '--fields', dest='fields', nargs="*", help="Key:value pairs" )
	
	return arg_parser, imodeled_schemas
	
def main():
	arg_parser = _create_args_parser()
	args = arg_parser.parse_args()
	#run_with_dataserver( environment_dir=args.env_dir, 
	#					 function=lambda: _change_attributes(args) )

if __name__ == '__main__':
	main()