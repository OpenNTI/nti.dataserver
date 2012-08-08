from __future__ import print_function, unicode_literals

from zope.deprecation import deprecated

from _repoze_adpater import _RepozeEntityIndexManager

deprecated( 'RepozeUserIndexManager', 'Use _repoze_adpater._RepozeUserIndexManager' )
class RepozeUserIndexManager(_RepozeEntityIndexManager):
	pass

deprecated( 'RepozeUserIndexManagerFactory', 'Use _repoze_adpater_RepozeEntityIndexManagerFactory' )	
class RepozeUserIndexManagerFactory(object):
	pass
		
deprecated('ruim_factory', 'Use _repoze_adpater.IRepozeEntityIndexManager')	
def ruim_factory(*args, **kwargs):
	return RepozeUserIndexManagerFactory()
