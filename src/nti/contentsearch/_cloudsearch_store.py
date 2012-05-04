from zope import interface

from persistent import Persistent
from nti.contentsearch.interfaces import ICloudSearchStore

from nti.contentsearch.exfm.cloudsearch import connect_cloudsearch

import logging
logger = logging.getLogger( __name__ )
	
# -----------------------------------

AWS_CS_PARAMS = {'aws_access_key_id': (str, None),
				 'aws_secret_access_key': (str, None),
				 'is_secure': (bool, True),
				 'host': (str, 'cloudsearch.us-east-1.amazonaws.com'), 
				 'port': (int, None), 
				 'proxy': (str, None), 
				 'proxy_port': (int, None),
				 'proxy_user': (str, None),
				 'proxy_pass': (str, None) }

class CloudSearchStore(Persistent):
	interface.implements(ICloudSearchStore)
	
	def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
				 is_secure=True, host='cloudsearch.us-east-1.amazonaws.com', port=None, 
				 proxy=None, proxy_port=None, proxy_user=None, proxy_pass=None,
				 debug=0, https_connection_factory=None, path='/'):
		
		super(CloudSearchStore, self).__init__()
		kwargs = dict(locals())
		kwargs.pop('self' , None)
		self._v_connection = connect_cloudsearch(**kwargs)
		self._set_aws_domains()

	def _set_aws_domains(self):
		self._v_domains = {}
		for d in self.get_aws_domains():
			self._v_domains[d.domain_name] = d
					
	@property
	def connection(self):
		return self.get_connection()
	
	@property
	def ntisearch(self):
		return self.get_domain(domain_name='ntisearch')
	
	def get_connection(self):
		return self._v_connection
		
	def get_aws_domains(self):
		domains = self.connection.get_domains()
		return domains
		
	def get_domain(self, domain_name):
		domain = self._v_domains.get(domain_name, None)
		return domain
	
if __name__ == '__main__':
	import os
	AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'AKIAJ42UUP2EUMCMCZIQ')
	AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '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')
	cs = CloudSearchStore(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
	
	from nti.contentsearch._cloudsearch_index import create_search_domain
	create_search_domain(cs.connection)
