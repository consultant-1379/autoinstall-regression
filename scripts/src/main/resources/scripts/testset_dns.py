"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    Laura Forbes
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants


class DNSClient(GenericTest):
    """
    Test the 'dns-client' LITP item type.
    Item Types verified are 'dns-client' and 'nameserver'.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(DNSClient, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])
        self.redhatutils = RHCmdUtils()

    def tearDown(self):
        """ Teardown run after every test """

        super(DNSClient, self).tearDown()

    @attr('all', 'revert', 'system_check', 'dns', 'dns_tc01')
    def test_01_p_verify_dns(self):
        """
        Description:
            Check that domain names in /etc/resolv.conf file match the model.
            Ensure domain name returned by nslookup of
                                    the MS IP is in resolv.conf and model.
            Test that IP of all nodes are pingable from MS.

        Actions:
            For each node:
            1. Check all modelled 'dns-client' items on node
            2. Create a list containing all properties of type "search"
            3. Check that all search items listed are in /etc/resolv.conf
            4. Get all nameservers under this dns-client
            5. Create a list of the nameservers from /etc/resolv.conf
            6. Create a list of the nameservers from the model
            7. Check that the nameservers are listed and in the correct order
        """

        for node in self.all_nodes:
            node_name = node["name"]

            # 1. Check all modelled 'dns-client' items on node
            dns_client = self.find(self.ms_node, node["url"],
                                   "dns-client", assert_not_empty=False)

            if not dns_client:
                self.log("info", node_name + ": No 'dns_client' defined.")
                continue

            dns_client = dns_client[0]

            # 2. Create a list containing all properties of type "search"
            search = self.get_props_from_url(self.ms_node, dns_client,
                                             filter_prop="search")
            list_search = search.split(',')

            # 3. Check that all search items listed are in /etc/resolv.conf
            resolv_conf = self.get_file_contents(
                node_name, test_constants.RESOLV_CFG_FILE)
            for domain in list_search:
                self.assertTrue(
                    self.is_text_in_list(domain, resolv_conf),
                    "{0}: domain '{1}' in model not in {2}".format(
                        node_name, domain, test_constants.RESOLV_CFG_FILE))

            # 4. Get all nameservers under this dns-client
            nameservers = self.find(self.ms_node, dns_client, "nameserver",
                                    assert_not_empty=False)
            # 5. Create a list of the nameservers from /etc/resolv.conf
            resolv_c_names_list = []
            for line in resolv_conf:
                if line.startswith('nameserver'):
                    resolv_c_names_list.append(line)

            # 6. Create a list of the nameservers from the model
            model_namesers = {}
            index_list = []
            for name in nameservers:
                props = self.get_props_from_url(self.ms_node, name)
                model_namesers[props['position']] = props['ipaddress']
                index_list.append(int(props['position']))

            # The reason for adding indexes to a list and operating on that
            # list is to cater for a case where a user sets a nameserver at
            # positions 1 and 3, or 2 and 3 etc.
            index_list.sort()
            nameservers = []
            for i in index_list:
                nameservers.append('nameserver {0}'
                                   .format(model_namesers[str(i)]))

            # 7. Check that the nameservers are listed and in the correct order
            self.assertTrue(resolv_c_names_list == nameservers)
