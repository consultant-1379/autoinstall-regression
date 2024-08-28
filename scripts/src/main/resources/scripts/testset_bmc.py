"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    Marco Gibboni
"""

from litp_generic_test import GenericTest, attr


class Bmc(GenericTest):
    """
    Test the Bmc LITP extension type.
    """

    def setUp(self):
        """ Setup Variables for every test """
        super(Bmc, self).setUp()
        # GET MODEL INFO
        self.model = self.get_model_names_and_urls()
        self.all_nodes = self.model["nodes"][:]
        self.ms_node = self.model["ms"][0]["name"]
        """ expected properties """
        self.bmc_props = sorted([
                            'ipaddress',
                            'password_key',
                            'username'
                        ])

    def tearDown(self):
        """ Teardown run after every test """
        super(Bmc, self).tearDown()

    def compare_bmc_props(self, right_list, props_list):
        """
            This function checks if the expected
            properties are in the list
            passed as parameter
        """
        for key in range(0, len(right_list)):
            if right_list[key] not in props_list:
                self.log('info', "The property '{0}' is missing!"\
                        .format(right_list[key]))
                return False
        return True

    @attr('all', 'revert', 'system_check', 'bmc', 'bmc_tc01')
    def test_01_check_bmc_props(self):
        """
        Description:
            [Blade item extends System item]
            A. Find all blade items (only blade may contain bmc item)
            B. Find all bmc items in each blade found
            C. Check bmc property values
        Actions:
            A.
                1. Find all blade items
                2. Assert blade name is not empty
            B.
                1. Find all bmc items
                2. All the bmc item properties must be
                    set and present
            C.
                1. Assert that IP address is reachable
        """
        # A1. Find all blade items
        for node in self.all_nodes:
            blades = self.find(self.ms_node, node['url'], \
                                "blade", assert_not_empty=False)
            if not blades:
                self.log('info', "There's no blade " +\
                                "in: {0}".format(node['name']))
            else:
                for blade in blades:
                    blade_values = self.get_props_from_url(self.ms_node, blade)
                    # A2. Assert blade name is not empty
                    self.assertNotEqual("", blade_values["system_name"])
                    # B1. Find all bmc items
                    bmcs = self.find(self.ms_node, node['url'], \
                                        "bmc", assert_not_empty=False)
                    if not bmcs:
                        self.log('info', "There's no bmc item " +\
                                        "in this blade: {0}".format(blade))
                    else:
                        for bmc in bmcs:
                            # B2. All the bmc item properties must be
                            #       set and present
                            prop_values = \
                                    self.get_props_from_url(self.ms_node, bmc)
                            prop_names = prop_values.keys()
                            same_lists = \
                                    self.compare_bmc_props(self.bmc_props,\
                                                            sorted(prop_names))
                            self.assertTrue(same_lists)
                            for key in prop_values:
                                self.assertNotEqual("", prop_values[key])
                            self.log('info', "All the required properties" +\
                                            " for this bmc item are present" +\
                                            " and set: {0}".format(bmc))
                            # C1. Assert that IP address is reachable
                            in_network = self.is_ip_pingable(self.ms_node, \
                                        "{0}".format(prop_values['ipaddress']))
                            self.assertTrue(in_network)
                            self.log('info', "BMC ip address " +\
                                    "{0} ".format(prop_values['ipaddress']) +\
                                    "is in network")
