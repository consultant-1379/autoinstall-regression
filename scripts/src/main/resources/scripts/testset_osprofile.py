"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    James Langan
"""

from litp_generic_test import GenericTest, attr
import test_constants
import re


class OSProfile(GenericTest):
    """
    Test the 'os-profile' LITP item type.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(OSProfile, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])
        self.required_props = ["name",
                               "kopts_post",
                               "breed",
                               "version",
                               "path",
                               "arch"]

    def tearDown(self):
        """ Teardown run after every test """

        super(OSProfile, self).tearDown()

    @attr('all', 'revert', 'system_check', 'osprofile', 'osprofile_tc01')
    def test_01_p_verify_os_profile(self):
        """
        Description:
            Test the 'os-profile' LITP item type.
            Verify that all 'os-profile' properties  modelled in LITP are
            configured appropriately on all nodes.

        Actions:
            1. For each node:
                a. Find all modelled 'os-profile' items.
                b. Get all 'os-profile' properties.
                c. Use command to get breed, architecture and version.
                d. Verify breed, architecture and version are as expected.
                e. Verify OS post-kernel options in '/proc/cmdline'
                f. Verify path exists on the Management Server
        """
        # 1. For each node check all modelled 'os-profile' items  are correct.
        for node in self.all_nodes:
            name = node["name"]
            # a. find modelled os-profiles for node/ms
            osprofiles = self.find(self.ms_node, node["url"], "os-profile",
                                 assert_not_empty=False)

            for osprofile in osprofiles:
                # b. get all 'os-profile' properties
                props = self.get_props_from_url(self.ms_node, osprofile)

                # c. Use check redhat rpm installed command to get info.
                cmd = "/bin/rpm -qa '*release-server*'"
                stdout, stderr, rc = self.run_command(node["name"], cmd)
                self.assertNotEqual([], stdout)
                self.assertEqual([], stderr)
                self.assertEqual(0, rc)

                # Output of command is in following format
                # redhat-release-server-7.9-3.el7.x86_64
                output = re.split('[-|.]', stdout[0])

                # d. Verify breed, architecture and version are as expected.
                breed = output[0]
                arch = output[-1]
                version = output[-2]
                # Taking expected el7 from output and adding rh.
                # Need to do so to allow verification of version property.
                if props["breed"] == 'redhat':
                    version = 'rh' + version

                self.log("info", name + " Verifying 'breed' is {0}"\
                                                .format(props["breed"]))
                self.assertEqual(props["breed"], breed)
                self.log("info", name + " Verifying 'arch' is {0}"\
                                                 .format(props["arch"]))
                self.assertEqual(props["arch"], arch)
                self.log("info", name + " Verifying 'version' is {0}"\
                                                 .format(props["version"]))
                self.assertEqual(props["version"], version)

                # e. Verify OS post-kernel options
                file_to_check = test_constants.KERNEL_CMDLINE_CONFIG_FILE
                expected = props["kopts_post"]
                self.log("info", name + " Verifying 'kopts_post' is {0}"\
                                                .format(props["kopts_post"]))
                stdout = self.get_file_contents(node["name"], file_to_check)
                self.assertTrue(self.is_text_in_list(expected, stdout), \
                       "{0} not in {1}".format(expected, file_to_check))

                # f. Verify path exists on the Management Server
                self.log("info", name + " Verifying 'path' {0} exists on MS"\
                                                 .format(props["path"]))
                self.assertTrue(self.remote_path_exists(self.ms_node,
                                                        props["path"],
                                                        expect_file=False,
                                                        su_root=False),
                               "path {0} does not exist".format(props["path"]))
