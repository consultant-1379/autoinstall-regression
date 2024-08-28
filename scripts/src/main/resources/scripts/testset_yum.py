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


class Yum(GenericTest):
    """
    Test the 'yum_extension' LITP item type.
    Item Types verified are 'base_url', 'cache_metadata',
    'ms_url_path' and 'name'.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(Yum, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])
        self.redhatutils = RHCmdUtils()

    def tearDown(self):
        """ Teardown run after every test """

        super(Yum, self).tearDown()

    def _yum_base_url(self, node_name, yum_base_url):
        """
        Description:
            Ensure path specified by base_url exists and is reachable from node

        Args:
            node_name (str): The node being tested.
            yum_base_url (str): The URL defined for the item in the model.

        Actions:
            a. If base_url is a local path, ensure path exists on node.
            b. If url is a path on MS or other external path, ensure
                path exists and is reachable from node.
        """
        # a. If url is a local path, ensure path exists on node
        if "file://" in yum_base_url:
            path_on_node = yum_base_url.split("file://")[1]
            self.assertTrue(self.remote_path_exists(node_name,
                path_on_node, expect_file=False),
                    "{0} does not exist on {1}.".format(
                        path_on_node, node_name))

        # b. If url is a path on MS or other external path, ensure
        #       path exists and is reachable from node
        else:
            self.assertTrue(self.check_repo_url_exists(node_name,
                yum_base_url + "/"), "URL {0} not reachable from {1}.".format(
                    yum_base_url, node_name))

    @attr('all', 'revert', 'system_check', 'yum', 'yum_tc01')
    def test_01_p_yum(self):
        """
        Description:
            Compare yum repolist with /etc/yum.repos.d/
            For each repository config file, make sure it has a 'name'
                    property and either a 'baseline' or 'ms_url_path' property
            For each 'yum-repository' type item in model tree, compare
                    it with its .repo file in /etc/yum.repos.d/

        Actions:
            For each node:
            1. Compare yum repolist with /etc/yum.repos.d/
                a. Run the "yum repolist" command on the node
                b. Create list to hold names of enabled repositories returned
                c. Run command to list contents of /etc/yum.repos.d/ directory
                d. For each repository returned from "yum repolist", check that
                        it has a .repo file in the /etc/yum.repos.d/ directory

            2. For each repository config file, make sure it has a 'name'
                    property and either a 'baseline' or 'ms_url_path' property
                a. Run command to output contents of .repo file
                b. Assert that 'name' property is defined in .repo file
                c. Assert that 'baseurl' or 'ms_url_path' is in .repo file

            3. For each 'yum-repository' type item in model tree, compare
                    it with its .repo file in /etc/yum.repos.d/
                a. Check for any modelled 'yum-repository' items on nodes
                For each 'yum-repository' item type:
                b. Create dictionary to contain properties of path of item
                c. Assert that a .repo file exists in
                        /etc/yum.repos.d/ for the item
                d. Get the contents of the .repo file
                e. If cache_metadata is set to false, ensure that
                        metadata_expire is defined in the .repo file
                f. If cache_metadata is set to true, ensure that
                        metadata_expire is not defined in the .repo file
                g. Ensure a 'base_url' or 'ms_url_path' property is
                        present in model for item
                If base_url is defined:
                h. Ensure path specified by base_url exists
                If ms_url_path is defined:
                i. Ensure path exists on MS

        """

        for node in self.all_nodes:
            node_name = node["name"]

            # 1. Compare yum repolist with /etc/yum.repos.d/
            # 1a. Run the "yum repolist" command on the node
            cmd = self.redhatutils.check_yum_repo_cmd()
            stdout, stderr, rc = self.run_command(node_name, cmd)
            self.assertEqual(stderr, [])
            self.assertEqual(rc, 0)

            # 1b. Create list to hold names of enabled repositories returned
            repo_list = []
            for item in stdout:
                # Only take the names of the enabled repositories:
                item = item.split(' ')[0]
                # Don't take headings:
                if item not in ["Loaded", "repo", "repolist:"]:
                    repo_list.append(item)

            # 1c. Run command to list contents of /etc/yum.repos.d/ directory
            etc_yum_repo = "/etc/yum.repos.d/"
            yum_conf_dir = self.list_dir_contents(node_name, etc_yum_repo)

            # 1d. For each repository returned from "yum repolist", check that
            #       it has a .repo file in the /etc/yum.repos.d/ directory

            updated_repo_list = [x for x in repo_list if x != ":"]

            for repo in updated_repo_list:
                check_repo = repo + ".repo"
                self.assertTrue(
                    check_repo in yum_conf_dir, "yum repolist item"
                    " '{0}' is not in /etc/yum.repos.d/ on {1}".format(
                                    repo, node_name))

                # 2. For each repository config file, make sure it has
                # a 'name' property and either a 'baseline' or 'ms_url_
                # path' property

                # 2a. Run command to output contents of .repo file
                file_path = "/etc/yum.repos.d/{0}.repo".format(repo)
                repo_file = self.get_file_contents(node_name, file_path)

                # 2b. Assert that 'name' property is defined in .repo file
                self.assertTrue(any("name" in s for s in repo_file))

                # 2c. Assert that 'baseurl' or 'ms_url_path' is in .repo
                # file
                self.assertTrue(any("baseurl" in s for s in repo_file) or
                                any("ms_url_path" in t for t in stdout))

            # 3. For each 'yum-repository' type item in model tree,
            # compare it with its .repo file in /etc/yum.repos.d/

            # 3a. Check for any modelled 'yum-repository' items on nodes
            yum_paths = self.find(self.ms_node, node["url"],
                                  "yum-repository", assert_not_empty=False)

            # For each 'yum-repository' item type:
            for path in yum_paths:
                # 3b. Create dictionary to contain properties of path of
                # item
                prop_yum = [self.get_props_from_url(self.ms_node, path)]

                for entry in prop_yum:
                    # 3c. Assert that a .repo file exists in
                    #       /etc/yum.repos.d/ for the item
                    yum_repo_name = entry['name'] + '.repo'
                    self.assertTrue(
                        any(yum_repo_name in s for s in yum_conf_dir),
                        "Yum repository {0} in model on {1} but"
                            " {2} not in /etc/yum.repos.d/".format(
                                entry['name'], node_name, yum_repo_name))

                    # 3d. Get the contents of the .repo file
                    file_path = "/etc/yum.repos.d/{0}".format(
                        yum_repo_name)
                    repo_content = self.get_file_contents(
                        node_name, file_path)

                    # If cache_metadata is defined in model item:
                    if 'cache_metadata' in entry:
                        # 3e. If cache_metadata is set to false,
                        # ensure that metadata_expire is defined in the
                        # .repo file
                        if entry['cache_metadata'] == "false":
                            self.assertTrue(
                                any("metadata_expire" in s for s
                                                 in repo_content))
                        # 3f. If cache_metadata is set to true,
                        # ensure that metadata_expire is not defined in
                        # the .repo file
                        else:
                            self.assertFalse(
                                any("metadata_expire" in s for s
                                                 in repo_content))

                    # 3g. Ensure a 'base_url' or 'ms_url_path' property
                    #       is present in model for item
                    self.assertTrue(
                        'base_url' in entry or 'ms_url_path' in
                        entry, "No URL property defined in {0}. Either a "
                            "'base_url' property or 'ms_url_path' "
                               "property must be defined.".format(
                            entry['name']))

                    # If base_url is defined:
                    if 'base_url' in entry:
                        # 3h. Ensure path specified by base_url exists
                        self._yum_base_url(node_name,
                                           entry['base_url'])

                    # If ms_url_path is defined:
                    elif 'ms_url_path' in entry:
                        # 3i. Ensure path exists on MS
                        yum_ms_url = entry['ms_url_path']
                        pkg_path_on_ms = "/var/www/html" + yum_ms_url
                        self.assertTrue(self.remote_path_exists(
                            self.ms_node,
                            pkg_path_on_ms, expect_file=False),
                                "'ms_url_path' {0} modelled in {1} on {2} "
                                "does not exist on MS.".format(
                                    pkg_path_on_ms, entry['name'],
                                    node_name))
