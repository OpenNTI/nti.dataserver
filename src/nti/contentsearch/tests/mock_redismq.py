import six

QUEUE_NAME = u'%r:queue' 
QUEUESET = u'QUEUESET' # the set which holds all queues

class RedisMQ(object):
    
    def __init__(self, redis):
        self.redis = redis
        
    def normalize(self, item):
        if isinstance(item, six.string_types):
            return unicode(item)
        else:
            raise ValueError("data must be a string")
        
    def _internal_queue_name(self, queue):
        result = QUEUE_NAME % self.normalize(queue)
        return unicode(result)
     
    def queue_add(self, queue, value, ttl=None):
        queue, value = self.normalize(queue), self.normalize(value)
            
        uuid = self.redis.incr("%r:UUID" % queue)
        key = '%r:%d' % (queue, uuid)
        self.redis.set(key, value)
        if ttl is not None:
            self.redis.expire(key, ttl)
    
        internal_queue_name = self._internal_queue_name(queue)
        if uuid == 1:
            self.redis.sadd(QUEUESET, queue)

        res = self.redis.lpush(internal_queue_name, key)
        return res

    def queue_get(self, queue, softget=False): 
        lkey = self._internal_queue_name(queue)
        if not softget:
            okey = self.redis.rpop(lkey)
        else:
            okey = self.redis.lindex(lkey, "-1")
    
        if okey is None:
            return None
     
        okey = self.normalize(okey)
        val = self.redis.get(okey)
        c = 0 if not softget else self.redis.incr('%r:refcount' % okey)
        return {'key':okey, 'value':val, 'count':c}
      
    def queue_del(self, queue, okey):
        """
            DELetes an element from redis (not from the queue).
            Its important to make sure a GET was issued before a DEL.
            the return value contains the key and value
        """
        queue, okey = self.normalize(queue), self.normalize(okey)
        val = self.redis.delete(okey)
        return {'key':okey, 'value':val}
    
    def queue_len(self, queue):
        lkey = self._internal_queue_name(queue)
        ll = self.redis.llen(lkey)
        return ll

    def queue_all(self):
        sm = self.redis.smembers(QUEUESET)
        return {'queues': sm}

    def _safe_rename(self, src, dst):
        try:
            return self.redis.rename(src, dst)
        except:
            return False
    
    def _del_internal_key(self, okey):
        okey = self.normalize(okey)
        nkey = '%r:lock' % okey
        ren = self._safe_rename(okey, nkey) # rename key
        if not ren:
            return None
    
        val, delk = self.redis.pipeline().get(nkey).delete(nkey).execute()
        return {'key':okey, 'value':val} if delk else None
    
    def queue_tail(self, queue, keyno=10, delete_obj=False): 
        """
            TAIL follows on GET, but returns keyno keys instead of only one key.
            keyno could be a LLEN function over the queue list, but it lends almost the same effect.
            LRANGE could too fetch the latest keys, even if there was less than keyno keys. MGET could be used too.
            TODO: does DELete belongs here ?
        """
        lkey = self._internal_queue_name(queue)
        multivalue = []
        for _ in range(keyno):
            nk = self.redis.rpop(lkey)
            if nk != None:
                t = self.normalize(nk)
            else:
                continue
    
            okey = t
            if delete_obj:
                v = self._del_internal_key(okey)
                if v is None: continue
                v = v['value']
            else:
                v = self.redis.get(t)
    
            multivalue.append({'key': okey, 'value': self.normalize(v)})
        
        return multivalue
    
    def queue_getdel(self, queue):
        lkey = self._internal_queue_name(queue)
        okey = self.redis.rpop(lkey) # take from queue's list
        if okey == None:
            return None
        else:
            return self._del_internal_key(okey)
                   
    def queue_count_elements(self, queue):
        try:
            lkey = '%r*' % self.normalize(queue)
            ll = self.redis.keys(lkey)
            return {"objects":len(ll)}
        except Exception, e:
            return {"error" : str(e)}

    def queue_last_items(self, queue, count=10):
        """
            returns a list with the last count items in the queue
        """
        lkey = self._internal_queue_name(queue)
        multivalue = self.redis.lrange(lkey, 0, count-1)
        return multivalue
 
def test_op(mq, queue='myqueue'):
    for x in xrange(10):
        uuid = mq.queue_add(queue, u'sample-%r' % x)
        print uuid
    print mq.queue_get(queue)
    print mq.queue_len(queue)
    print mq.queue_all()
    print mq.queue_tail(queue, 5, True)
    print mq.queue_len(queue)
    #print mq.queue_count_elements(queue)
    print mq.queue_last_items(queue)
   
if __name__ == '__main__':
    from nti.dataserver.tests.mock_redis import InMemoryMockRedis
    redis = InMemoryMockRedis()
    mq = RedisMQ(redis)
    test_op(mq)
