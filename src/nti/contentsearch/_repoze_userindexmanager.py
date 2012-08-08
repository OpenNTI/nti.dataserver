from __future__ import print_function, unicode_literals

from zope.deprecation import deprecated

from _repoze_adpater import _RepozeUserIndexManager

deprecated( 'RepozeUserIndexManager', 'Use _repoze_adpater._RepozeUserIndexManager' )
class RepozeUserIndexManager(_RepozeUserIndexManager):
	pass

deprecated( 'RepozeUserIndexManagerFactory', 'Use _repoze_adpater_RepozeUserIndexManagerFactory' )	
class RepozeUserIndexManagerFactory(object):
	pass
		
deprecated('ruim_factory', 'Use _repoze_adpater.IRepozeUserIndexManager')	
def ruim_factory(*args, **kwargs):
	return RepozeUserIndexManagerFactory()
