#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009-2010:
#    Gabes Jean, naparuba@gmail.com
#    Gerhard Lausser, Gerhard.Lausser@consol.de
#    Sebastien Coavoux, s.coavoux@free.fr
#
# This file is part of Shinken.
#
# Shinken is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Shinken is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Shinken.  If not, see <http://www.gnu.org/licenses/>.


#
# This file is used to test host- and service-downtimes.
#

import os
import sys
import time
import random

from shinken_test import unittest

from shinken_modules import TestConfig
from shinken.comment import Comment

from mock_livestatus import mock_livestatus_handle_request


sys.setcheckinterval(10000)



@mock_livestatus_handle_request
class TestConfigBig(TestConfig):
    def setUp(self):
        start_setUp = time.time()
        self.setup_with_file('etc/shinken_5r_100h_2000s.cfg')
        Comment.id = 1
        self.testid = str(os.getpid() + random.randint(1, 1000))
        self.init_livestatus()
        print "Cleaning old broks?"
        self.sched.conf.skip_initial_broks = False
        self.sched.brokers['Default-Broker'] = {'broks' : {}, 'has_full_broks' : False}
        self.sched.fill_initial_broks('Default-Broker')

        self.update_broker()
        print "************* Overall Setup:", time.time() - start_setUp
        # add use_aggressive_host_checking so we can mix exit codes 1 and 2
        # but still get DOWN state
        host = self.sched.hosts.find_by_name("test_host_000")
        host.__class__.use_aggressive_host_checking = 1



    def test_negate(self):
        # test_host_005 is in hostgroup_01
        # 20 services   from  400 services
        hostgroup_01 = self.sched.hostgroups.find_by_name("hostgroup_01")
        host_005 = self.sched.hosts.find_by_name("test_host_005")
        test_ok_00 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_00")
        query = """GET services
Columns: host_name description
Filter: host_name = test_host_005
Filter: description = test_ok_00
OutputFormat: python
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(query)
        pyresponse = eval(response)
        print len(pyresponse)
        query = """GET services
Columns: host_name description
OutputFormat: python
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(query)
        allpyresponse = eval(response)
        print len(allpyresponse)
        query = """GET services
Columns: host_name description
Filter: host_name = test_host_005
Filter: description = test_ok_00
And: 2
Negate:
OutputFormat: python
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(query)
        negpyresponse = eval(response)
        print len(negpyresponse)
        # only test_ok_00 + without test_ok_00 must be all services
        self.assert_(len(allpyresponse) == len(pyresponse) + len(negpyresponse))

        query = """GET hosts
Columns: host_name num_services
Filter: host_name = test_host_005
OutputFormat: python
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(query)
        numsvc = eval(response)
        print response, numsvc

        query = """GET services
Columns: host_name description
Filter: host_name = test_host_005
Filter: description = test_ok_00
Negate:
OutputFormat: python
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(query)
        numsvcwithout = eval(response)
        self.assert_(numsvc[0][1] - 1 == len(numsvcwithout))

    def test_worst_service_state(self):
        # test_host_005 is in hostgroup_01
        # 20 services   from  400 services
        hostgroup_01 = self.sched.hostgroups.find_by_name("hostgroup_01")
        host_005 = self.sched.hosts.find_by_name("test_host_005")
        test_ok_00 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_00")
        test_ok_01 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_01")
        test_ok_04 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_04")
        test_ok_16 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_16")
        objlist = []
        for service in [svc for host in hostgroup_01.get_hosts() for svc in host.services]:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(2, objlist)
        self.update_broker()
        #h_request = """GET hosts\nColumns: name num_services_ok num_services_warn num_services_crit num_services_unknown worst_service_state worst_service_hard_state\nFilter: name = test_host_005\nColumnHeaders: on\nResponseHeader: fixed16"""
        h_request = """GET hosts\nColumns: num_services_warn num_services_crit num_services_unknown worst_service_state worst_service_hard_state\nFilter: name = test_host_005\nColumnHeaders: off\nResponseHeader: off"""
        #hg_request = """GET hostgroups\nColumns: name num_services_ok num_services_warn num_services_crit num_services_unknown worst_service_state worst_service_hard_state\nFilter: name = hostgroup_01\nColumnHeaders: on\nResponseHeader: fixed16"""
        hg_request = """GET hostgroups\nColumns: num_services_warn num_services_crit num_services_unknown worst_service_state worst_service_hard_state\nFilter: name = hostgroup_01\nColumnHeaders: off\nResponseHeader: off"""

        # test_ok_00
        # test_ok_01
        # test_ok_04
        # test_ok_16
        h_response, keepalive = self.livestatus_broker.livestatus.handle_request(h_request)
        hg_response, keepalive = self.livestatus_broker.livestatus.handle_request(hg_request)
        print "ho_reponse", h_response
        print "hg_reponse", hg_response
        self.assert_(h_response == hg_response)
        self.assert_(h_response == """0;0;0;0;0
""")

        # test_ok_00
        # test_ok_01 W(S)
        # test_ok_04
        # test_ok_16
        self.scheduler_loop(1, [[test_ok_01, 1, 'WARN']])
        self.update_broker()
        h_response, keepalive = self.livestatus_broker.livestatus.handle_request(h_request)
        hg_response, keepalive = self.livestatus_broker.livestatus.handle_request(hg_request)
        self.assert_(h_response == hg_response)
        self.assert_(h_response == """1;0;0;1;0
""")

        # test_ok_00
        # test_ok_01 W(S)
        # test_ok_04 C(S)
        # test_ok_16
        self.scheduler_loop(1, [[test_ok_04, 2, 'CRIT']])
        self.update_broker()
        h_response, keepalive = self.livestatus_broker.livestatus.handle_request(h_request)
        hg_response, keepalive = self.livestatus_broker.livestatus.handle_request(hg_request)
        self.assert_(h_response == hg_response)
        self.assert_(h_response == """1;1;0;2;0
""")

        # test_ok_00
        # test_ok_01 W(H)
        # test_ok_04 C(S)
        # test_ok_16
        self.scheduler_loop(2, [[test_ok_01, 1, 'WARN']])
        self.update_broker()
        h_response, keepalive = self.livestatus_broker.livestatus.handle_request(h_request)
        hg_response, keepalive = self.livestatus_broker.livestatus.handle_request(hg_request)
        self.assert_(h_response == hg_response)
        self.assert_(h_response == """1;1;0;2;1
""")

        # test_ok_00
        # test_ok_01 W(H)
        # test_ok_04 C(H)
        # test_ok_16
        self.scheduler_loop(2, [[test_ok_04, 2, 'CRIT']])
        self.update_broker()
        h_response, keepalive = self.livestatus_broker.livestatus.handle_request(h_request)
        hg_response, keepalive = self.livestatus_broker.livestatus.handle_request(hg_request)
        self.assert_(h_response == hg_response)
        self.assert_(h_response == """1;1;0;2;2
""")

    def test_stats(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        svc1 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_00")
        print svc1
        svc2 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_15")
        print svc2
        svc3 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_16")
        print svc3
        svc4 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_05")
        print svc4
        svc5 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_11")
        svc6 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_01")
        svc7 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_03")
        self.scheduler_loop(1, [[svc1, 1, 'W'], [svc2, 1, 'W'], [svc3, 1, 'W'], [svc4, 2, 'C'], [svc5, 3, 'U'], [svc6, 2, 'C'], [svc7, 2, 'C']])
        self.update_broker()
        # 1993O, 3xW, 3xC, 1xU

        request = """GET services
Filter: contacts >= test_contact
Stats: state != 9999
Stats: state = 0
Stats: state = 1
Stats: state = 2
Stats: state = 3"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_6_______________\n%s\n%s\n' % (request, response)
        self.assert_(response == '2000;1993;3;3;1\n')

        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

    def test_statsgroupby(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        svc1 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_00")
        print svc1
        svc2 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_15")
        print svc2
        svc3 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_16")
        print svc3
        svc4 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_05")
        print svc4
        svc5 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_11")
        svc6 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_01")
        svc7 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_03")
        self.scheduler_loop(1, [[svc1, 1, 'W'], [svc2, 1, 'W'], [svc3, 1, 'W'], [svc4, 2, 'C'], [svc5, 3, 'U'], [svc6, 2, 'C'], [svc7, 2, 'C']])
        self.update_broker()
        # 1993O, 3xW, 3xC, 1xU

        request = 'GET services\nFilter: contacts >= test_contact\nStats: state != 9999\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3\nStatsGroupBy: host_name'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.contains_line(response, 'test_host_005;20;17;3;0;0'))
        self.assert_(self.contains_line(response, 'test_host_007;20;18;0;1;1'))
        self.assert_(self.contains_line(response, 'test_host_025;20;18;0;2;0'))
        self.assert_(self.contains_line(response, 'test_host_026;20;20;0;0;0'))

        request = """GET services
Stats: state != 9999
StatsGroupBy: state
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.contains_line(response, '0;1993'))
        self.assert_(self.contains_line(response, '1;3'))
        self.assert_(self.contains_line(response, '2;3'))
        self.assert_(self.contains_line(response, '3;1'))
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

    def test_hostsbygroup(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hostsbygroup
ColumnHeaders: on
Columns: host_name hostgroup_name
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

    def test_servicesbyhostgroup(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET servicesbyhostgroup
Filter: host_groups >= up
Stats: has_been_checked = 0
Stats: state = 0
Stats: has_been_checked != 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 4
Stats: state = 0
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsAnd: 3
Stats: state = 1
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 1
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 1
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
Stats: state = 2
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 2
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 2
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
Stats: state = 3
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 3
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 3
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
StatsGroupBy: hostgroup_name
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        tic = time.clock()
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        tac = time.clock()
        print "livestatus duration %f" % (tac - tic)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

        # Again, without Filter:
        request = """GET servicesbyhostgroup
Stats: has_been_checked = 0
Stats: state = 0
Stats: has_been_checked != 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 4
Stats: state = 0
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsAnd: 3
Stats: state = 1
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 1
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 1
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
Stats: state = 2
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 2
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 2
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
Stats: state = 3
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 3
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 3
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
StatsGroupBy: hostgroup_name
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

    def test_childs(self):
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hosts
Columns: childs
Filter: name = test_host_0
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))
        request = """GET hosts
Columns: childs
Filter: name = test_router_0
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

    def test_thruk_servicegroup(self):
        self.print_header()
        now = time.time()
        self.update_broker()
        #---------------------------------------------------------------
        # get services of a certain servicegroup
        # test_host_0/test_ok_0 is in
        #   servicegroup_01,ok via service.servicegroups
        #   servicegroup_02 via servicegroup.members
        #---------------------------------------------------------------
        request = """GET services
Columns: host_name service_description
Filter: groups >= servicegroup_01
OutputFormat: csv
ResponseHeader: fixed16
"""
        # 400 services => 400 lines + header + empty last line
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "r1", response
        self.assert_(len(response.split("\n")) == 402)

        request = """GET servicegroups
Columns: name members
Filter: name = servicegroup_01
OutputFormat: csv
"""
        sg01 = self.livestatus_broker.livestatus.datamgr.rg.servicegroups.find_by_name("servicegroup_01")
        print "sg01 is", sg01
        # 400 services => 400 lines
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "r2", response
        # take first line, take members column, count list elements = 400 services
        self.assert_(len(((response.split("\n")[0]).split(';')[1]).split(',')) == 400)

    def test_sorted_limit(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        # now send the list of services to the broker in an unordered way
        sched_unsorted = '\n'.join(["%s;%s;%d" % (s.host_name, s.service_description, s.state_id) for s in self.sched.services])

        self.update_broker()
        #print "in ls test", self.livestatus_broker.rg.services._id_heap
        #for s in self.livestatus_broker.rg.services:
        #    print s.get_full_name()
        if hasattr(self.livestatus_broker.rg.services, "__iter__") and hasattr(self.livestatus_broker.rg.services, "itersorted"):
            print "ris__iter__", self.livestatus_broker.rg.services.__iter__
            print "ris__itersorted__", self.livestatus_broker.rg.services.itersorted
        i = 0
        while i < 10:
            print self.livestatus_broker.rg.services._id_heap[i]
            idx = self.livestatus_broker.rg.services._id_heap[i]
            print self.livestatus_broker.rg.services[idx].get_full_name()
            i += 1
        i = 0

        live_sorted = '\n'.join(sorted(["%s;%s;%d" % (s.host_name, s.service_description, s.state_id) for s in self.livestatus_broker.rg.services]))

        # Unsorted in the scheduler, sorted in livestatus
        self.assert_(sched_unsorted != live_sorted)
        sched_live_sorted = '\n'.join(sorted(sched_unsorted.split('\n'))) + '\n'
        sched_live_sorted = sched_live_sorted.strip()
        print "first of sched\n(%s)\n--------------\n" % sched_unsorted[:100]
        print "first of live \n(%s)\n--------------\n" % live_sorted[:100]
        print "first of sssed \n(%s)\n--------------\n" % sched_live_sorted[:100]
        print "last of sched\n(%s)\n--------------\n" % sched_unsorted[-100:]
        print "last of live \n(%s)\n--------------\n" % live_sorted[-100:]
        print "last of sssed \n(%s)\n--------------\n" % sched_live_sorted[-100:]
        # But sorted they are the same.
        self.assert_('\n'.join(sorted(sched_unsorted.split('\n'))) == live_sorted)

        svc1 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_00")
        print svc1
        svc2 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_15")
        print svc2
        svc3 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_16")
        print svc3
        svc4 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_05")
        print svc4
        svc5 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_11")
        svc6 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_01")
        svc7 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_03")
        self.scheduler_loop(1, [[svc1, 1, 'W'], [svc2, 1, 'W'], [svc3, 1, 'W'], [svc4, 2, 'C'], [svc5, 3, 'U'], [svc6, 2, 'C'], [svc7, 2, 'C']])
        self.update_broker()
        # 1993O, 3xW, 3xC, 1xU

        # Get all bad services from livestatus
        request = """GET services
Columns: host_name service_description state
ColumnHeaders: off
OutputFormat: csv
Filter: state != 0"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        # Get all bad services from the scheduler
        sched_bad_unsorted = '\n'.join(["%s;%s;%d" % (s.host_name, s.service_description, s.state_id) for s in self.sched.services if s.state_id != 0])
        # Check if the result of the query is sorted
        self.assert_('\n'.join(sorted(sched_bad_unsorted.split('\n'))) == response.strip())

        # Now get the first 3 bad services from livestatus
        request = """GET services
Limit: 3
Columns: host_name service_description state
ColumnHeaders: off
OutputFormat: csv
Filter: state != 0"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_6_______________\n%s\n%s\n' % (request, response)

        # Now compare the first 3 bad services with the scheduler data
        self.assert_('\n'.join(sorted(sched_bad_unsorted.split('\n'))[:3]) == response.strip())

        # Now check if all services are sorted when queried with a livestatus request
        request = """GET services
Columns: host_name service_description state
ColumnHeaders: off
OutputFormat: csv"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        # Again, get all bad services from the scheduler
        sched_bad_unsorted = '\n'.join(["%s;%s;%d" % (s.host_name, s.service_description, s.state_id) for s in self.sched.services])

        # Check if the result of the query is sorted
        ## FIXME LAUSSER self.assert_('\n'.join(sorted(sched_bad_unsorted.split('\n'))) == response.strip())



    # We look for the perf of the unhandled srv
    # page view of Thruk. We only enable it when we need
    # it's not a true test.
    def test_thruk_unhandled_srv_page_perf(self):
        # COMMENT THIS LINE to enable the bench and call
        # python test_livestatus.py TestConfigBig.test_thruk_unhandled_srv_page_perf
        return
        import cProfile
        cProfile.runctx('''self.do_test_thruk_unhandled_srv_page_perf()''', globals(), locals(), '/tmp/livestatus_thruk_perf.profile')

    def do_test_thruk_unhandled_srv_page_perf(self):
        self.print_header()

        objlist = []
        # We put 10% of elemetnsi n bad states
        i = 0
        for host in self.sched.hosts:
            i += 1
            if i % 10 == 0:
                objlist.append([host, 1, 'DOWN'])
            else:
                objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            i += 1
            if i % 10 == 0:
                objlist.append([service, 2, 'CRITICAL'])
            else:
                objlist.append([service, 0, 'OK'])
        self.scheduler_loop(2, objlist)
        self.update_broker()

        # We will look for the overall page loading time
        total_page = 0.0

        # First Query
        query_start = time.time()
        request = """
GET status
Columns: accept_passive_host_checks accept_passive_service_checks check_external_commands check_host_freshness check_service_freshness enable_event_handlers enable_flap_detection enable_notifications execute_host_checks execute_service_checks last_command_check last_log_rotation livestatus_version nagios_pid obsess_over_hosts obsess_over_services process_performance_data program_start program_version interval_length
OutputFormat: json
ResponseHeader: fixed16
"""
        print "Query 1 launched (Get overall status)"
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        #print response
        load_time = time.time() - query_start
        total_page += load_time
        print "Response time 1: %.3f" % load_time

        # Second Query
        query_start = time.time()
        request = """
GET hosts
Stats: name !=
StatsAnd: 1
Stats: check_type = 0
StatsAnd: 1
Stats: check_type = 1
StatsAnd: 1
Stats: has_been_checked = 0
StatsAnd: 1
Stats: has_been_checked = 0
Stats: active_checks_enabled = 0
StatsAnd: 2
Stats: has_been_checked = 0
Stats: scheduled_downtime_depth > 0
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 0
StatsAnd: 2
Stats: check_type = 0
Stats: has_been_checked = 1
Stats: state = 0
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: check_type = 1
Stats: has_been_checked = 1
Stats: state = 0
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: has_been_checked = 1
Stats: state = 0
Stats: scheduled_downtime_depth > 0
StatsAnd: 3
Stats: has_been_checked = 1
Stats: state = 1
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 1
Stats: acknowledged = 1
StatsAnd: 3
Stats: has_been_checked = 1
Stats: state = 1
Stats: scheduled_downtime_depth > 0
StatsAnd: 3
Stats: check_type = 0
Stats: has_been_checked = 1
Stats: state = 1
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: check_type = 1
Stats: has_been_checked = 1
Stats: state = 1
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: has_been_checked = 1
Stats: state = 1
Stats: active_checks_enabled = 1
Stats: acknowledged = 0
Stats: scheduled_downtime_depth = 0
StatsAnd: 5
Stats: has_been_checked = 1
Stats: state = 2
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 2
Stats: acknowledged = 1
StatsAnd: 3
Stats: has_been_checked = 1
Stats: state = 2
Stats: scheduled_downtime_depth > 0
StatsAnd: 3
Stats: check_type = 0
Stats: has_been_checked = 1
Stats: state = 2
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: check_type = 1
Stats: has_been_checked = 1
Stats: state = 2
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: has_been_checked = 1
Stats: state = 2
Stats: active_checks_enabled = 1
Stats: acknowledged = 0
Stats: scheduled_downtime_depth = 0
StatsAnd: 5
Stats: is_flapping = 1
StatsAnd: 1
Stats: flap_detection_enabled = 0
StatsAnd: 1
Stats: notifications_enabled = 0
StatsAnd: 1
Stats: event_handler_enabled = 0
StatsAnd: 1
Stats: check_type = 0
Stats: active_checks_enabled = 0
StatsAnd: 2
Stats: check_type = 1
Stats: active_checks_enabled = 0
StatsAnd: 2
Stats: accept_passive_checks = 0
StatsAnd: 1
Stats: state = 1
Stats: childs !=
StatsAnd: 2
OutputFormat: json
ResponseHeader: fixed16
"""
        print "Query 2 launched (Get hosts stistics)"
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        #print response
        load_time = time.time() - query_start
        total_page += load_time
        print "Response time 2: %.3f" % load_time

        # Now Query 3 (service stats)
        query_start = time.time()
        request = """
GET services
Stats: description !=
StatsAnd: 1
Stats: check_type = 0
StatsAnd: 1
Stats: check_type = 1
StatsAnd: 1
Stats: has_been_checked = 0
StatsAnd: 1
Stats: has_been_checked = 0
Stats: active_checks_enabled = 0
StatsAnd: 2
Stats: has_been_checked = 0
Stats: scheduled_downtime_depth > 0
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 0
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 0
Stats: scheduled_downtime_depth > 0
StatsAnd: 3
Stats: check_type = 0
Stats: has_been_checked = 1
Stats: state = 0
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: check_type = 1
Stats: has_been_checked = 1
Stats: state = 0
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: has_been_checked = 1
Stats: state = 1
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 1
Stats: scheduled_downtime_depth > 0
StatsAnd: 3
Stats: check_type = 0
Stats: has_been_checked = 1
Stats: state = 1
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: check_type = 1
Stats: has_been_checked = 1
Stats: state = 1
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: has_been_checked = 1
Stats: state = 1
Stats: acknowledged = 1
StatsAnd: 3
Stats: has_been_checked = 1
Stats: state = 1
Stats: host_state != 0
StatsAnd: 3
Stats: has_been_checked = 1
Stats: state = 1
Stats: host_state = 0
Stats: active_checks_enabled = 1
Stats: acknowledged = 0
Stats: scheduled_downtime_depth = 0
StatsAnd: 6
Stats: has_been_checked = 1
Stats: state = 2
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 2
Stats: scheduled_downtime_depth > 0
StatsAnd: 3
Stats: check_type = 0
Stats: has_been_checked = 1
Stats: state = 2
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: check_type = 1
Stats: has_been_checked = 1
Stats: state = 2
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: has_been_checked = 1
Stats: state = 2
Stats: acknowledged = 1
StatsAnd: 3
Stats: has_been_checked = 1
Stats: state = 2
Stats: host_state != 0
StatsAnd: 3
Stats: has_been_checked = 1
Stats: state = 2
Stats: host_state = 0
Stats: active_checks_enabled = 1
Stats: acknowledged = 0
Stats: scheduled_downtime_depth = 0
StatsAnd: 6
Stats: has_been_checked = 1
Stats: state = 3
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 3
Stats: scheduled_downtime_depth > 0
StatsAnd: 3
Stats: check_type = 0
Stats: has_been_checked = 1
Stats: state = 3
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: check_type = 1
Stats: has_been_checked = 1
Stats: state = 3
Stats: active_checks_enabled = 0
StatsAnd: 4
Stats: has_been_checked = 1
Stats: state = 3
Stats: acknowledged = 1
StatsAnd: 3
Stats: has_been_checked = 1
Stats: state = 3
Stats: host_state != 0
StatsAnd: 3
Stats: has_been_checked = 1
Stats: state = 3
Stats: host_state = 0
Stats: active_checks_enabled = 1
Stats: acknowledged = 0
Stats: scheduled_downtime_depth = 0
StatsAnd: 6
Stats: is_flapping = 1
StatsAnd: 1
Stats: flap_detection_enabled = 0
StatsAnd: 1
Stats: notifications_enabled = 0
StatsAnd: 1
Stats: event_handler_enabled = 0
StatsAnd: 1
Stats: check_type = 0
Stats: active_checks_enabled = 0
StatsAnd: 2
Stats: check_type = 1
Stats: active_checks_enabled = 0
StatsAnd: 2
Stats: accept_passive_checks = 0
StatsAnd: 1
OutputFormat: json
ResponseHeader: fixed16
"""
        print "Query 3 launched (Get services statistics)"
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        #print response
        load_time = time.time() - query_start
        total_page += load_time
        print "Response time 3: %.3f" % load_time

        # 4th Query
        query_start = time.time()
        request = """
GET comments
Columns: author comment entry_time entry_type expires expire_time host_name id persistent service_description source type
Filter: service_description !=
Filter: service_description =
Or: 2
OutputFormat: json
ResponseHeader: fixed16
"""
        print "Query 4 launched (Get comments)"
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        #print response
        load_time = time.time() - query_start
        total_page += load_time
        print "Response time 4: %.3f" % load_time

        # 5th Query
        query_start = time.time()
        request = """
GET downtimes
Columns: author comment end_time entry_time fixed host_name id start_time service_description triggered_by
Filter: service_description !=
Filter: service_description =
Or: 2
OutputFormat: json
ResponseHeader: fixed16
"""
        print "Query 5 launched (Get downtimes)"
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        #print response
        load_time = time.time() - query_start
        total_page += load_time
        print "Response time 5: %.3f" % load_time

        # 6th Query
        query_start = time.time()
        request = """
GET services
Filter: host_has_been_checked = 0
Filter: host_state = 0
Filter: host_has_been_checked = 1
And: 2
Or: 2
Filter: state = 1
Filter: has_been_checked = 1
And: 2
Filter: state = 3
Filter: has_been_checked = 1
And: 2
Filter: state = 2
Filter: has_been_checked = 1
And: 2
Or: 3
Filter: scheduled_downtime_depth = 0
Filter: acknowledged = 0
Filter: checks_enabled = 1
And: 3
And: 3
Stats: description !=
OutputFormat: json
ResponseHeader: fixed16
"""
        print "Query 6 launched (Get bad services)"
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        #print response
        load_time = time.time() - query_start
        total_page += load_time
        print "Response time 6: %.3f" % load_time

        # 7th Query
        query_start = time.time()
        request = """
GET services
Columns: accept_passive_checks acknowledged action_url action_url_expanded active_checks_enabled check_command check_interval check_options check_period check_type checks_enabled comments current_attempt current_notification_number description event_handler event_handler_enabled custom_variable_names custom_variable_values execution_time first_notification_delay flap_detection_enabled groups has_been_checked high_flap_threshold host_acknowledged host_action_url_expanded host_active_checks_enabled host_address host_alias host_checks_enabled host_comments host_groups host_has_been_checked host_icon_image_expanded host_icon_image_alt host_is_executing host_is_flapping host_name host_notes_url_expanded host_notifications_enabled host_scheduled_downtime_depth host_state icon_image icon_image_alt icon_image_expanded is_executing is_flapping last_check last_notification last_state_change latency long_plugin_output low_flap_threshold max_check_attempts next_check notes notes_expanded notes_url notes_url_expanded notification_interval notification_period notifications_enabled obsess_over_service percent_state_change perf_data plugin_output process_performance_data retry_interval scheduled_downtime_depth state state_type is_impact source_problems impacts criticity business_impact is_problem got_business_rule parent_dependencies
Filter: host_has_been_checked = 0
Filter: host_state = 0
Filter: host_has_been_checked = 1
And: 2
Or: 2
Filter: state = 1
Filter: has_been_checked = 1
And: 2
Filter: state = 3
Filter: has_been_checked = 1
And: 2
Filter: state = 2
Filter: has_been_checked = 1
And: 2
Or: 3
Filter: scheduled_downtime_depth = 0
Filter: acknowledged = 0
Filter: checks_enabled = 1
And: 3
And: 3
Limit: 150
OutputFormat: json
ResponseHeader: fixed16
"""
        print "Query 7 launched (Get bad service data)"
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        #print response
        load_time = time.time() - query_start
        total_page += load_time
        print "Response time 7: %.3f" % load_time

        print ""
        print "Overall Queries time: %.3f" % total_page

    def test_thruk_search(self):
        self.print_header()
        now = time.time()
        self.update_broker()
        # 99 test_host_099
        request = """GET comments
Columns: author comment entry_time entry_type expires expire_time host_name id persistent service_description source type
Filter: service_description !=
Filter: service_description =
Or: 2
Filter: comment ~~ 99
Filter: author ~~ 99
Or: 2
OutputFormat: csv
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "r1", response
        self.assert_(response == """
""")

        request = """GET downtimes
Columns: author comment end_time entry_time fixed host_name id start_time service_description triggered_by
Filter: service_description !=
Filter: service_description =
Or: 2
Filter: comment ~~ 99
Filter: author ~~ 99
Or: 2
OutputFormat: csv
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "r1", response
        self.assert_(response == """
""")

        request = """GET services
Columns: host_has_been_checked host_name host_state
Filter: description ~~ 99
Filter: groups >= 99
Filter: plugin_output ~~ 99
Filter: long_plugin_output ~~ 99
Filter: host_name ~~ 99
Filter: host_alias ~~ 99
Filter: host_address ~~ 99
Filter: host_groups >= 99
Filter: host_comments >= -1
Filter: host_downtimes >= -1
Filter: comments >= -1
Filter: downtimes >= -1
Or: 4
Or: 9
OutputFormat: csv
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "r1", response
        # test_host_099 matches by name
        # test_host_098 matches by address (test_host_098 has 127.0.0.99)
        self.assert_(response == """0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_098;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
0;test_host_099;0
""")

    def test_display_name(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hosts
Filter: name = test_router_0
Columns: name display_name"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assertEqual('test_router_0;display_router_0\n', response)
        request = """GET services
Filter: host_name = test_host_000
Filter: description = test_unknown_00
Columns: description host_name display_name"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == 'test_unknown_00;test_host_000;display_unknown_00\n')

if __name__ == '__main__':
    #import cProfile
    command = """unittest.main()"""
    unittest.main()