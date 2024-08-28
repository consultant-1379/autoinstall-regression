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
import test_constants


class Hosts(GenericTest):
    """
    Test the 'hosts' LITP item type.
    Item Type verified is 'alias'.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(Hosts, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])

    def tearDown(self):
        """ Teardown run after every test """

        super(Hosts, self).tearDown()

    @staticmethod
    def _check_pair(etc_hosts, ip_address, alias_names):
        """
        Description:
            Tests that the given (IP, Alias Names)
                    pair exists in the /etc/hosts file.

        Args:
            node_name (str): Name of the node being tested.
            etc_hosts (list): Contents of /etc/hosts as a list
            ip_address (str): IP to check.
            alias_names (list): List of alias names to check.

        Actions:
            a. For each line in the hosts file:
                b. Return True if the (IP, Alias Names) pair has been found.
            c. Return False if the pair has not been found.

        Returns:
            True (bool): If the pair has been found.
            False (bool): If the pair has not been found.
        """

        check_aliases = [ip_address]
        for alias in alias_names:
            check_aliases.append(alias)

        # For each line in the hosts file:
        for line in etc_hosts:
            # b. Return True if the (IP, Alias Names) pair has been found
            if all(x in line for x in check_aliases):
                return True

        # c. Return False if the pair has not been found
        return False

    @attr('all', 'revert', 'system_check', 'hosts', 'hosts_tc01')
    def test_01_p_verify_hosts(self):
        """
        Description:
            Check that alias names and IPs in /etc/hosts file match the model.
            Perform traceroute on each alias, ensuring it resolves to right IP.
        Actions:
            For each node:
                1. Check all modelled 'alias' items on node.
                2. Get the contents of /etc/hosts for this node
                For each 'alias' item type:
                    3. Create a dictionary of alias name and IP address pairs.
                    4. For each (Alias Name, IP) pair:
                        a. Retrieve the alias names.
                        b. Retrieve the IP address.
                        c. Ensure none of the alias names are hostname of MS.
                        d. Ensure that the (IP, Alias Names) pair
                                        exists in the /etc/hosts file.
        """
        for node in self.all_nodes:
            node_name = node["name"]

            # 1. Check all modelled 'alias' items on node
            alias = self.find(self.ms_node, node["url"], "alias",
                              assert_not_empty=False)
            # 2. Get the contents of /etc/hosts for this node
            etc_hosts = \
                self.get_file_contents(node_name, test_constants.ETC_HOSTS)

            # For each 'alias' item type:
            for path in alias:
                # 3. Create a dictionary of alias name and IP address pairs
                alias_ip = [self.get_props_from_url(self.ms_node, path)]

                # 4. For each (Alias Name, IP) pair:
                for entry in alias_ip:
                    # 3a. Retrieve the alias names
                    alias_names = entry['alias_names']
                    # Split the comma separated list
                    alias_names = alias_names.split(",")
                    # 3b. Retrieve the IP address
                    ip_address = entry['address']

                    # 3c. Ensure none of the alias names are the hostname of MS
                    for alias in alias_names:
                        self.assertTrue(
                            alias != self.ms_node,
                            "Alias name ({0}) cannot be the same as the "
                            "hostname of the management server.".format(alias))

                    # 3d. Ensure that the (IP, Alias Names) pair
                    #           exists in the /etc/hosts file
                    self.assertTrue(
                        self._check_pair(etc_hosts, ip_address, alias_names),
                        "{0}: IP {1} with alias names {2} does not exist in "
                        "/etc/hosts.".format(node_name, ip_address,
                                             alias_names)
                    )
