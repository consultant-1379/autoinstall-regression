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


class Service(GenericTest):
    """
    Test the Service LITP extension type.
    """

    def setUp(self):
        """ Setup Variables for every test """
        super(Service, self).setUp()
        self.model = self.get_model_names_and_urls()
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])
        self.ms_node = self.model["ms"][0]["name"]

    def tearDown(self):
        """ Teardown run after every test """
        super(Service, self).tearDown()

    @attr('all', 'revert', 'system_check', 'service', 'service_tc01')
    def test_01_check_service_items(self):
        """
        Description:
            A. Find all the service items in all the nodes (ms/peer nodes)
            B. Check whether the services are running and correctly set
        Actions:
            A
                1. Retrieve the service items in each node
            B
                1. Check whether the required property values are set
                2. Assert that the service is running
        """
        for node in self.all_nodes:
            # A1. Retrieve the service items in each node
            services = self.find(self.ms_node, node['url'], \
                                "service", assert_not_empty=False)
            if not services:
                self.log('info', "There's no service item " +\
                                "in: {0}".format(node['name']))
            else:
                for service in services:
                    service_values = \
                                self.get_props_from_url(self.ms_node, service)
                    # B1. Check whether the required property values are set
                    self.assertNotEqual("", service_values["cleanup_command"])
                    # B2. Assert that the service is running
                    _, std_err, r_code = \
                                self.get_service_status(node['name'], \
                                            service_values["service_name"])
                    self.assertEqual([], std_err)
                    self.assertEqual(0, r_code)
