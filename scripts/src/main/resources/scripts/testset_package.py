"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    Bryan O'Neill
"""

from litp_generic_test import GenericTest, attr


class Package(GenericTest):
    """
    Test the 'package' LITP item type.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(Package, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]

    def teardown(self):
        """ Teardown run after every test """

        super(Package, self).setUp()

    @attr('all', 'revert', 'system_check', 'package', 'package_tc01')
    def test_01_p_packages_installed(self):
        """
        Description:
            Test the 'package' LITP item type.
            Verify that all packages modelled in LITP are installed under the
            relevant node/ms. Verify that the installed package properties such
            as epoch and version correspond to the properties in the LITP
            model.

        Actions:
            1. Create a list of all nodes and MS to iterate over.
            2. For each node:
                a. Find all packages modelled for node/ms
                b. Get all package properties
                c. Check package is installed
                d. Check package epoch if not 0(default)
                e. Check package version if specified

        """
        # 1. Create a list of node items to iterate over. This list includes
        #    the MS as we need to check packages on it too.
        all_nodes = self.model["nodes"][:]
        all_nodes.extend(self.model["ms"][:])

        # 2. For each node/ms check all modelled packages are correct.
        for node in all_nodes:
            # a. find modelled packages for node/ms
            packages = self.find(self.ms_node, node["url"], "package",
                                 assert_not_empty=False)

            for package in packages:
                # b. get all package properties
                props = self.get_props_from_url(self.ms_node, package)

                # c. Check package is installed.
                cmd = "/bin/rpm -qa | grep {0}".format(props["name"])
                stdout, stderr, rc = self.run_command(node["name"], cmd)
                self.assertTrue(props["name"] in stdout[0])
                self.assertEqual(stderr, [])
                self.assertEqual(rc, 0)

                # d. Check package epoch if not 0(default)
                if not props["epoch"] == "0":
                    cmd = "/bin/rpm -q --qf \"%{{epoch}}\" {0}"\
                          .format(props["name"])
                    stdout, stderr, rc = self.run_command(node["name"], cmd)
                    self.assertEqual(stdout[0], props["epoch"])
                    self.assertEqual(stderr, [])
                    self.assertEqual(rc, 0)

                # e. Check package version if specified
                if "version" in props:
                    cmd = "/bin/rpm -q --qf \"%{{version}}\" {0}"\
                          .format(props["name"])
                    stdout, stderr, rc = self.run_command(node["name"], cmd)
                    self.assertEqual(stdout[0], props["version"])
                    self.assertEqual(stderr, [])
                    self.assertEqual(rc, 0)
