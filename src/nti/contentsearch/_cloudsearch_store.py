from zope import interface

from persistent import Persistent
from nti.contentsearch.interfaces import ICloudSearchStore

from nti.contentsearch.exfm.cloudsearch import connect_cloudsearch

import logging
logger = logging.getLogger( __name__ )
	
# -----------------------------------

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
		
	@property
	
	def get_domain(self, domain_name='ntisearch'):
		domain = self.connection.get_domain(domain_name)
		return domain
	


if __name__ == '__main__':
	import os
	AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'AKIAJ42UUP2EUMCMCZIQ')
	AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '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')
	cs = CloudSearchStore(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
	domain = cs.get_domain()
	print domain