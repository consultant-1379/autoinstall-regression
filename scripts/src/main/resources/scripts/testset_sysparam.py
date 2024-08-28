"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    Brian Carey
"""

from litp_generic_test import GenericTest, attr
import test_constants


class Sysparam(GenericTest):
    """Test the 'sysparam' LITP item type."""

    def setUp(self):
        """
        Description:
            Runs before every single test
        Results:
            The super class prints out diagnostics and variables
            common to all tests available
        """

        super(Sysparam, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Perform Test Cleanup
        Results:
            Items used in the test are cleaned up and the
            super class prints out end test diagnostics
        """
        super(Sysparam, self).tearDown()

    @attr('all', 'revert', 'system_check', 'sysparams', 'sysparams_tc01')
    def test_01_p_sysparam_properties(self):
        """
        Description:
            Test the 'sysparam' LITP item type.
            Verify that all sysparams modelled in LITP are installed under the
            relevant node/ms. Verify that the properties of each sysparam
            are equal to the modelled values

        Actions:
            1. Create a list of all nodes and MS to iterate over.
            2. For each node:
                a. Find the urls for the items of type 'sysparam' in model
                b. If no sysparams in model - test passes.
                c. Get the contents of the sysctl config file
                d. Get properties of each sysparam
                e. Verify that the properties of each modelled sysparam
                    are equal to that in the sysctl config file

        Result:
            Returns True if the correct sysparams have been added or if
            there are no sysparams item types in the LITP model.
        """

        # 1. Create a list of all nodes and MS to iterate over.
        all_nodes = self.model["nodes"][:]
        all_nodes.extend(self.model["ms"][:])

        config_filepath = test_constants.SYSCTL_CONFIG_FILE

        # 2. Iterate over all nodes in model
        for node in all_nodes:

            # a. Find the urls for the items of type 'sysparam' in model
            sysparams = self.find(self.ms_node, node["url"], "sysparam",
                                  assert_not_empty=False)

            # b. If no sysparams in model - test passes.
            if not sysparams:

                self.log("info", "No items of type 'sysparam' in {0} - Pass"
                         .format(node["name"]))

                continue

            self.log("info", "Printing out sysctl config file for {0}"
                     .format(node["name"]))

            # c. Get the contents of the sysctl config file
            sysctl = self.get_file_contents(node["name"], config_filepath)

            newsysctl = [item.split(' = ') for item in sysctl]

            # d. Get properties of each of sysparam
            for sysparam in sysparams:
                self.log("info", "Printing sysparam URL: {0}".format(sysparam))

                props = self.get_props_from_url(self.ms_node, sysparam)

                self.log("info", "Printing out sysparam properties: {0}"
                         .format(props))

                # f. Verify that the properties of each modelled
                #    sysparam is equal to that in the sysctl config
                #    file
                self.log("info", "Checking the properties in the model"
                                 " against what is in the sysctl config file.")

                self.assertTrue([props["key"], props["value"]] in newsysctl)
