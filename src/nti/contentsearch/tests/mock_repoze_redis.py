import time
import threading

from nti.contentsearch import _repoze_redis_store

class MockRepozeRedisStorageService(_repoze_redis_store._RepozeRedisStorageService):
		
	use_trx_runner = False
	
	def _spawn_index_listener(self):
		def read_idx_msgs():
			while not self.stop:
				time.sleep(1)
				if not self.stop:
					self.read_process_index_msgs()
		
		th = threading.Thread(target=read_idx_msgs)
		th.start()
		return th

	def initial_wait(self):
		return 0.5

	