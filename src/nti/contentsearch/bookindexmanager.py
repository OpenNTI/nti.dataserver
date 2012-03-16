from nti.contentsearch._whoosh_bookindexmanager import WhooshBookIndexManager

class BookIndexManager(WhooshBookIndexManager):
	def __init__(self, indexdir="/tmp/", indexname="prealgebra"):
		super(BookIndexManager, self).__init__(indexname=indexname, indexdir=indexdir)





