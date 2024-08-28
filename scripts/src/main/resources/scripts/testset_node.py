"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     July 2015
@author:    Marco Gibboni
"""

from litp_generic_test import GenericTest, attr


class Node(GenericTest):
    """
    Test the Node LITP item type.
    """

    def setUp(self):
        """ Setup Variables for every test """
        super(Node, self).setUp()
        self.model = self.get_model_names_and_urls()
        self.all_nodes = self.model["nodes"][:]
        self.ms_node = self.model["ms"][0]

    def tearDown(self):
        """ Teardown run after every test """
        super(Node, self).tearDown()

    @attr('all', 'revert', 'system_check', 'node', 'node_tc01')
    def test_01_check_node_settings(self):
        """
        Description:
            A. Find all the nodes for each cluster
            B. Assert that the nodes have required properties set
                and required children present
        Actions:
            A.
                1. Through each cluster, find all the nodes
            B.
                1. In the node, check required properties are correctly set
                    and not empty
                2. Search required children and assert that they are present
        """
        all_clusters = self.model["clusters"][:]
        for cluster in all_clusters:
            # A1. Through each cluster, find all the nodes
            nodes = self.find(self.ms_node['name'], cluster['url'], "node")
            for node in nodes:
                self.log('info', "Checking required properties and " +\
                                    "children of {0}".format(node))
                node_values = self.get_props_from_url(\
                                                self.ms_node['name'], node)
                # B1. In the node, check required properties
                #       are correctly set and not empty
                self.assertNotEqual("", node_values['hostname'])
                self.assertTrue(node_values['is_locked'] in ["true", "false"])
                self.log('info', "Required properties are set.")
                # B2. Search required children and
                #       assert that they are present
                network_interface = self.find_children_of_collect(\
                                            self.ms_node['name'], \
                                            node, \
                                            "network-interface")
                self.assertNotEqual([], network_interface)
                os_profile = self.get_props_from_url(self.ms_node['name'], \
                                            node + "/os")
                self.assertNotEqual([], os_profile)
                storage_profile = self.get_props_from_url(\
                            self.ms_node['name'], node + "/storage_profile")
                self.assertNotEqual([], storage_profile)
                system = self.get_props_from_url(self.ms_node['name'], \
                                            node + "/system")
                self.assertNotEqual([], system)
