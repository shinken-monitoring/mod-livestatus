
from __future__ import division


import os
import random
from random import randint
import socket
import threading
import time

from shinken.objects.module import Module
from shinken_modules import TestConfig
from shinken_test import time_hacker, unittest
from test_livestatus import LiveStatusTest

from livestatus.livestatus_wait_query import LiveStatusWaitQuery
from livestatus.livestatus_query import LiveStatusQuery


class Test_WaitQuery(LiveStatusTest):

    def test_wait_query(self):
        request = b'''GET hosts
WaitObject: gstarck_test
WaitCondition: last_check >= 1419007690
WaitTimeout: 10000
WaitTrigger: check
Columns: last_check state plugin_output
Filter: host_name = gstarck_test
Localtime: 1419007690
OutputFormat: python
KeepAlive: on
ResponseHeader: fixed16
ColumnHeaders: off

'''

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        self.assertEqual(2, len(response), 'should contains Wait + Query')
        self.assertIsInstance(response[0], LiveStatusWaitQuery)
        self.assertIsInstance(response[1], LiveStatusQuery)



class TestFull_WaitQuery(TestConfig):
    ''' "Full" test : that is with connection to livestatus socket
    '''

    def tearDown(self):
        # stop thread
        self.livestatus_broker.interrupted = True
        self.lql_thread.join()
        super(TestFull_WaitQuery, self).tearDown()

    def setUp(self):
        super(TestFull_WaitQuery, self).setUp()
        time_hacker.set_real_time()
        self.testid = str(os.getpid() + random.randint(1, 1000))
        self.modconf = Module({'module_name': 'LiveStatus',
            'module_type': 'livestatus',
            'port': str(random.randint(50000, 65534)),
            'pnp_path': 'tmp/pnp4nagios_test' + self.testid,
            'host': '127.0.0.1',
            'name': 'test',
            'modules': ''
        })
        self.init_livestatus(self.modconf)

    def init_livestatus(self, conf):
        super(TestFull_WaitQuery, self).init_livestatus(conf)
        self.sched.conf.skip_initial_broks = False
        self.sched.brokers['Default-Broker'] = {'broks' : {}, 'has_full_broks' : False}
        self.sched.fill_initial_broks('Default-Broker')
        self.update_broker()
        self.nagios_path = None
        self.livestatus_path = None
        self.nagios_config = None
        self.lql_thread = threading.Thread(target=self.livestatus_broker.manage_lql_thread, name='lqlthread')
        self.lql_thread.start()
        # wait for thread to init
        time.sleep(3)

    def query_livestatus(self, data, ip=None, port=None, timeout=60):
        if ip is None:
            ip = self.modconf.host
        if port is None:
            port = self.modconf.port
        port = int(port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(timeout)
            s.connect((ip, port))
            s.send(data)
            s.shutdown(socket.SHUT_WR)
            ret = []
            while True:
                data = s.recv(1024)
                #print("received: %r" % data)
                if not data:
                    return b''.join(ret)
                ret.append(data)
        finally:
            s.close()


    def test_wait_query_1(self):
        wait_timeout_sec = randint(1, 3)
        request = b'''GET hosts
WaitObject: test_host_0
WaitCondition: last_check >= 1419007690
WaitTimeout: %s
WaitTrigger: check
Columns: last_check state plugin_output
Filter: host_name = test_host_0
Localtime: 1419007690
OutputFormat: python
KeepAlive: on
ResponseHeader: fixed16
ColumnHeaders: true

''' % (wait_timeout_sec * 1000) # WaitTimeout header field is in millisecs

        t0 = time.time()
        response = self.query_livestatus(request)
        t1 = time.time()
        self.assertLess(wait_timeout_sec, t1 - t0,
                        'wait query should take up to the requested WaitTimeout (%s sec) to complete' %
                        wait_timeout_sec)
        goodresponse = "200          13\n[[0, 0, '']]\n"
        self.assertEqual(goodresponse, response)



if __name__ == '__main__':
    unittest.main()
