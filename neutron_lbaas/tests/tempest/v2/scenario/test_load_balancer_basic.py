# Copyright 2015 Rackspace Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log as logging

from neutron_lbaas.tests.tempest.lib import config
from neutron_lbaas.tests.tempest.lib import test
from neutron_lbaas.tests.tempest.v2.clients import listeners_client
from neutron_lbaas.tests.tempest.v2.clients import load_balancers_client
from neutron_lbaas.tests.tempest.v2.clients import members_client
from neutron_lbaas.tests.tempest.v2.clients import pools_client
from neutron_lbaas.tests.tempest.v2.scenario import base

CONF = config.CONF

LOG = logging.getLogger(__name__)


class TestLoadBalancerBasic(base.BaseTestCase):

    """
    This test checks basic load balancing.
    The following is the scenario outline:
    1. Create an instance
    2. SSH to the instance and start two servers
    3. Create a load balancer with two members and with ROUND_ROBIN algorithm
       associate the VIP with a floating ip
    4. Send NUM requests to the floating ip and check that they are shared
       between the two servers.
    """
    def setUp(self):
        super(TestLoadBalancerBasic, self).setUp()
        self.server_ips = {}
        self.server_fixed_ips = {}
        self._create_security_group_for_test()
        self._set_net_and_subnet()

        mgr = self.get_client_manager()
        auth_provider = mgr.auth_provider
        client_args = [auth_provider, 'network', 'regionOne']

        self.load_balancers_client = (
            load_balancers_client.LoadBalancersClientJSON(*client_args))
        self.listeners_client = (
            listeners_client.ListenersClientJSON(*client_args))
        self.pools_client = pools_client.PoolsClientJSON(*client_args)
        self.members_client = members_client.MembersClientJSON(*client_args)

    def tearDown(self):
        super(TestLoadBalancerBasic, self).tearDown()

    @test.services('compute', 'network')
    def test_load_balancer_basic(self):
        self._create_servers()
        self._start_servers()
        self._create_load_balancer()
        self._check_load_balancing()

        lbs = self.load_balancers_client.list_load_balancers()
        for lb_entity in lbs:
            lb_id = lb_entity['id']
            lb = self.load_balancers_client.get_load_balancer_status_tree(
                lb_id).get('loadbalancer')
            for listener in lb.get('listeners'):
                for pool in listener.get('pools'):
                    self.delete_wrapper(self.pools_client.delete_pool,
                                        pool.get('id'))
                    self._wait_for_load_balancer_status(lb_id)
                self.delete_wrapper(self.listeners_client.delete_listener,
                                    listener.get('id'))
                self._wait_for_load_balancer_status(lb_id)
            self.delete_wrapper(
                self.load_balancers_client.delete_load_balancer, lb_id)
