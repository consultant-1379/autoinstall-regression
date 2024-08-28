'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    James Langan
'''

from litp_generic_test import GenericTest, attr
import re


class Firewall(GenericTest):
    '''
    Test the 'firewall' LITP item type.
    Following commands are used to verify firewalls towards
    MS and Managed Nodes.
    'sudo iptables -t filter -S',
    'sudo iptables -t nat -S',
    'sudo iptables -t mangle -S',
    'sudo iptables -t raw -S',
    'sudo ip6tables -t filter -S',
    'sudo ip6tables -t mangle -S',
    'sudo ip6tables -t raw -S'
    '''
    IP_TABLES = "iptables"
    IP6_TABLES = "ip6tables"

    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        # 1. Call super class setup
        super(Firewall, self).setUp()
        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.model["ms"][0]["fw_rules"] = []

        # Dict used to store expected output from iptables/ip6tables
        # command for each packet matching table option.
        self.iptable_options = {'iptables': {'filter': [],
                                             'nat': [],
                                             'mangle': [],
                                             'raw': []},
                                'ip6tables': {'filter': [],
                                              'mangle': [],
                                              'raw': []}}

        # Default Firewall rules on Management Server.
        self.ms_default_fw_rules = [
            ['tcp', '443', 'ACCEPT', 'INPUT'],
            ['tcp', '443', 'ACCEPT', 'OUTPUT'],
            ['tcp', '8140,8139,9999', 'ACCEPT', 'INPUT'],
            ['tcp', '8140,8139,9999', 'ACCEPT', 'OUTPUT'],
            ['tcp',
             '4369,9100,9101,9102,9103,9104,9105,61613,61614',
             'ACCEPT',
             'INPUT'],
            ['tcp',
             '4369,9100,9101,9102,9103,9104,9105,61613,61614',
             'ACCEPT',
             'OUTPUT'],
            ['udp', '123', 'ACCEPT', 'INPUT'],
            ['udp', '123', 'ACCEPT', 'OUTPUT'],
            ['tcp', '80', 'ACCEPT', 'INPUT'],
            ['tcp', '80', 'ACCEPT', 'OUTPUT'],
            ['udp', '67,68,69', 'ACCEPT', 'INPUT'],
            ['udp', '67,68,69', 'ACCEPT', 'OUTPUT'],
            ['tcp', '22', 'ACCEPT', 'INPUT'],
            ['tcp', '22', 'ACCEPT', 'OUTPUT'],
            ['999 drop all', 'DROP', 'INPUT'],
            ['1999 drop all', 'DROP', 'OUTPUT']]

        # Default Firewall rules on Managed Nodes.
        self.mn_default_fw_rules = [
            ['tcp', '8140,8139,9999', 'ACCEPT', 'INPUT'],
            ['tcp', '8140,8139,9999', 'ACCEPT', 'OUTPUT'],
            ['tcp',
             '4369,9100,9101,9102,9103,9104,9105,61614',
             'ACCEPT',
             'INPUT'],
            ['tcp',
             '4369,9100,9101,9102,9103,9104,9105,61614',
             'ACCEPT',
             'OUTPUT'],
            ['udp', '123', 'ACCEPT', 'INPUT'],
            ['udp', '123', 'ACCEPT', 'OUTPUT'],
            ['tcp', '80', 'ACCEPT', 'INPUT'],
            ['tcp', '80', 'ACCEPT', 'OUTPUT'],
            ['tcp', '22', 'ACCEPT', 'INPUT'],
            ['tcp', '22', 'ACCEPT', 'OUTPUT'],
            ['999 drop all', 'DROP', 'INPUT'],
            ['1999 drop all', 'DROP', 'OUTPUT']]

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Ensure true is turned on after test run
            2. Call superclass teardown
        Results:
            Items used in the test are cleaned up and the
        """
        # 1. Call superclass teardown
        super(Firewall, self).tearDown()

    def get_litp_ms_fw_config_data(self):
        """
        Description:
            Get MS Firewall Configuration from LITP Model and store in local
            data structure.
        Args: None
        Actions:
            a. Find modelled 'firewall-node-config' item type for MS.
               a1. Get all 'firewall-node-config' properties.
               a2. Verify mandatory 'firewall-node-config' property.
            b. Find modelled 'firewall-rule' item types for MS.
            c. Add MS firewall rules list to Model Data Structure.
        Results:
            True. If "firewall-node-config" exists.
            False. If "firewall-node-config" does not exist.
        """
        # There is a maximum of 1 firewall-node-config items per node
        # a. Find modelled 'firewall-node-config' item type for MS.
        firewall_node_cfg_urls = self.find(self.ms_node, "/ms",
                                          "firewall-node-config",
                                           assert_not_empty=False)

        if firewall_node_cfg_urls:
            firewall_node_cfg_url = firewall_node_cfg_urls[0]

            # a. Get all 'firewall-node-config' properties.
            props = self.get_props_from_url(self.ms_node,
                                            firewall_node_cfg_url)

            # a2. Verify mandatory 'firewall-node-config' property.
            self.assertTrue("drop_all" in props)

            # b. Find modelled 'firewall-rule' item types for MS.
            fw_rules_urls = self.find(self.ms_node,
                                      firewall_node_cfg_url,
                                      "firewall-rule",
                                      assert_not_empty=False)

            if fw_rules_urls:
                # c. Add MS firewall rules list to Model Data Structure.
                self.model["ms"][0].update({"fw_rules": fw_rules_urls})
            else:
                self.log('info', self.ms_node + ': No LITP firewall rules')
            return True
        else:
            return False

    def get_litp_cluster_fw_config_data(self):
        """
        Description:
            Get Firewall Config for all Clusters in LITP Model and store in
            data structure.
        Args: None
        Actions:
            a. Create a list of Clusters to iterate over.
            b. Initialise Cluster Firewall information in Model.
            c. Find modelled 'firewall-cluster-config' item type.
            d. Update Cluster "firewall-cluster-config" in model structure
            e. Get all 'firewall-node-config' properties
            f. Verify mandatory 'firewall-node-config' property types.
            g. Find modelled 'firewall-rule' item types for cluster.
            h. Update Cluster firewall rules in model data structure.
        Results:
            True.
        """
        # a. Create a list of Clusters to iterate over.
        all_clusters = self.model["clusters"][:]
        for cluster in all_clusters:
            # b. Initialise Cluster Firewall info in model data structure.
            cluster["fw_cluster_config"] = None
            cluster["fw_rules"] = []

            # c. Find modelled 'firewall-cluster-config' item type.
            fw_cluster_cfg_urls = self.find(self.ms_node, cluster["url"],
                                            "firewall-cluster-config",
                                            assert_not_empty=False)

            if fw_cluster_cfg_urls:
                fw_cluster_cfg_url = fw_cluster_cfg_urls[0]
                # d. Update Cluster in Model with "firewall-cluster-config"
                cluster.update({"fw_cluster_config": fw_cluster_cfg_url})

                # e. get all 'firewall-node-config' properties
                props = self.get_props_from_url(self.ms_node,
                                                fw_cluster_cfg_url)

                # f. Verify mandatory 'firewall-node-config' property types.
                self.assertTrue("drop_all" in props)

                # g. Find modelled 'firewall-rule' item types for Cluster.
                fw_rules_urls = self.find(self.ms_node,
                                          fw_cluster_cfg_url,
                                          "firewall-rule",
                                          assert_not_empty=False)

                if fw_rules_urls:
                    # h. Update Cluster firewall rules in model data structure.
                    cluster.update({"fw_rules": fw_rules_urls})

    def get_litp_managed_node_fw_config_data(self):
        """
        Description:
            Get Firewall Config for all Managed Nodes in LITP Model and
            store in data structure.
        Args: None
        Actions:
            For each Managed Node:
                a. Find modelled 'firewall-node-config' item type.
                b. Get all 'firewall-node-config' properties
                c. Verify mandatory 'firewall-node-config' property types.
                d. Find modelled 'firewall-rule' item types for each node.
                e. Store node firewall rules in model data structure.
        Results:
            True.
        """
        # Get all Managed node Specific firewall-node-config urls in
        # the LITP tree
        all_nodes = self.model["nodes"][:]
        for node in all_nodes:
            # Initialise.
            node["fw_node_config"] = None
            node["fw_rules"] = []
            # a. Find modelled 'firewall-node-config' item type.
            fw_node_cfg_urls = self.find(self.ms_node,
                                         node["url"],
                                         "firewall-node-config",
                                         assert_not_empty=False)

            if fw_node_cfg_urls:
                fw_node_cfg_url = fw_node_cfg_urls[0]
                node.update({"fw_node_config": fw_node_cfg_url})
                # b. Get all 'firewall-node-config' properties
                props = self.get_props_from_url(self.ms_node,
                                                fw_node_cfg_url)

                # c. Verify mandatory 'firewall-node-config' property types.
                self.assertTrue("drop_all" in props)

                # d. Find modelled 'firewall-rule' item types for each node.
                fw_rules_urls = self.find(self.ms_node,
                                          fw_node_cfg_url,
                                          "firewall-rule",
                                          assert_not_empty=False)

                if fw_rules_urls:
                    # e. Store firewall rules in data structure.
                    node.update({"fw_rules": fw_rules_urls})
                else:
                    self.log('info', node["name"] + ': No LITP firewall rules')

    def _verify_iptables(self, node, rules_list, command='iptables',
                                                 table='filter'):
        """
        Description:
            Verify that iptables/ip6tables contain firewall rules.
        Args:
            node (str): node on which to verify the iptable/ip6table.
            rules_list (list): list of firewall rules to verify. (Mandatory)
            command (str): iptables or ip6tables.
            table (str): only following options supported
                  iptables: 'filter', 'nat', 'mangle' and 'raw'
                  ip6tables: 'filter', 'mangle' and 'raw'
        Actions:
            a. Ensure rules_list is not empty.
            b. Execute iptables/ip6tables command on desired node.
            c. Verify that iptables/ip6tables contained rules.
            d. Assert False if any rules were missing from tables.
        Results:
            False if any rule missing from iptables/ip6tables.
            Otherwise True.
        """
        # a. Ensure rules_list is not empty.
        # If there are no rules to verify, this function should not be called.
        self.assertNotEqual([], rules_list)

        # b. Execute iptables/ip6tables command on desired node.
        cmd = "/sbin/{0} -t {1} -S".format(command, table)

        iptables_out, std_err, rc = self.run_command(node,
                                                     cmd,
                                                     su_root=True)

        self.assertEquals([], std_err)
        self.assertNotEqual([], iptables_out)
        self.assertEquals(0, rc)

        fw_rules_not_matched = rules_list[:]

        # c. Verify that iptables/ip6tables contained rules.
        self.log('info', str(node) + ' ' + command + ' ' + table + ' Matching')
        # Loop through Firewall Rules list
        for fw_rule in rules_list:
            # Loop through the lines output by iptables/ip6tables
            for line in iptables_out:
                # E.G. fw_rule and it's corresponding rules.
                # ['201 dnsudp', 'INPUT', 'udp', 'ACCEPT', 'NEW', '53']
                # If line contains all of the rules from the firewall.
                if all((rule in line) for rule in fw_rule):
                    print "Line matched: {0} with {1}".format(line,
                                                              fw_rule)
                    fw_rules_not_matched.remove(fw_rule)

        # d. Assert False if any rules were missing from tables.
        self.assertEqual([], fw_rules_not_matched, "Unmatched rules : \
                                            {0}".format(fw_rules_not_matched))

    def _verify_iptables_default_ports(self, node):
        """
        Description:
            Verify Default Ports opened by linuxfirewall plugin.
        Args:
            node (str): node on which to verify the iptable/ip6table.
        Actions:
            a. For each node, verify the iptables contain default ports.
        Results:
            True.
        """
        ip_tables_check_commands = [self.IP_TABLES, self.IP6_TABLES]

        # a. For each node, verify the iptables contain default ports.
        if node is self.ms_node:
            for command in ip_tables_check_commands:
                self._verify_iptables(node, self.ms_default_fw_rules, command)
        else:
            for command in ip_tables_check_commands:
                self._verify_iptables(node, self.mn_default_fw_rules, command)

    def _process_fw_rule_properties(self, properties):
        """
        Description:
            Get all properties associated with a firewall rule and
            modify those properties to enable matching with content of
            iptables and ip6tables command.
        Args:
            propertiess (list): properties of firewall rule.
        Actions:
            a. Default command to 'iptables' and table option to 'filter'
            b. Check firewall-rule has a name which is mandatory.
            c. Modify 'dport' property to enable matching later.
            d. Modify 'action' property to enable matching later.
            e. Handle and remove 'provider'.
            f. Remove 'log_level' property.
            g. Handle 'table' property.
            h. Handle 'proto' property.
            i. Handle 'chain' property.
            j. Fill iptable_options with expected firewall information
        Results:
            True.
        """
        # a. Default iptable to iptables and table to 'filter'.
        iptable = 'both'
        table = 'filter'

        properties1 = {}

        # b. Check firewall-rule has a name.
        self.assertTrue("name" in properties)

        # c. Modify 'dport' property to enable matching later.
        # Ranges in LITP model properties are displayed using '-'.
        # In iptables and ip6tables, ranges are displayed using ':'
        if 'dport' in properties:
            properties['dport'] = re.sub('["-]+', ':', properties['dport'])

        # d. Modify 'action' property to enable matching later.
        # LITP model 'action' property is displayed in lowercase.
        # In iptables and ip6tables, actions are displayed uppercase.
        if 'action' in properties:
            properties['action'] = properties['action'].upper()

        # e. Handle 'provider' property to enable matching later.
        # 'provider' dictates if info is included in iptables or ip6tables.
        # if absent, info is included in both iptables and ip6tables.
        if 'provider' in properties:
            if 'ip6tables' == properties['provider']:
                iptable = self.IP6_TABLES
            elif 'iptables' == properties['provider']:
                iptable = self.IP_TABLES
            # Need to delete 'provider' as this is not in iptables/ip6tables
            del properties['provider']

        # f. Remove 'log_level' property to enable matching later.
        if 'log_level' in properties:
            # Need to delete 'log_level' as this is not in iptables/ip6tables
            del properties['log_level']

        # g. Handle 'table' property.
        if 'table' in properties:
            table = properties['table']
            # Need to delete 'table' as this is not in iptables/ip6tables
            del properties['table']

        # h. handle proto property
        if 'proto' in properties:
            if properties['proto'] == 'all':
                del properties['proto']

        # i. Handle 'chain' property to enable matching later.
        # If no 'chain' property is included, there will be 2 chain
        # related lines in iptables/ip6tables output.
        # One each for 'INPUT' and 'OUTPUT'
        properties, properties1 = self.handle_chain_property(properties)

        rules_list = []
        rules_list_a = list(properties.values())
        rules_list.append(rules_list_a)

        if properties1:
            rules_list_b = list(properties1.values())
            rules_list.append(rules_list_b)

        # j. Fill iptable_options with expected firewall information
        # for iptables and/or ip6tables.
        if iptable == 'both':
            self.iptable_options[self.IP_TABLES][table].extend(rules_list)
            self.iptable_options[self.IP6_TABLES][table].extend(rules_list)
        else:
            self.iptable_options[iptable][table].extend(rules_list)

    @staticmethod
    def handle_chain_property(properties):
        """
        Description:
            Handle chain property for a firewall-rule.
            If no 'chain' property is included, there will be 2 chain
            related lines in iptables/ip6tables output. One each for 'INPUT'
            and 'OUTPUT'
            INPUT chains will have '0' added to the firewall-rule name
            property when represented in ip(6)tables if loopback firewall.
            OUTPUT chains will have '1' added to firewall-rule name property in
            iptables. If loopback firewall rule, '10' will be added.

        Args:
            properties (list): firewall rule properties.

        Returns:
            list, list. list of properties to be used when matching INPUT and
                        OUTPUT chains in ip(6)tables respectively.
        """
        if 'chain' not in properties:
            properties['chain'] = 'INPUT'
            properties1 = properties.copy()
            properties1['chain'] = 'OUTPUT'
            if 'iniface' in properties:
                properties['name'] = '"0' + properties['name']
            else:
                properties['name'] = '"' + properties['name']
            if 'iniface' in properties1:
                properties1['name'] = '"10' + properties1['name']
            else:
                properties1['name'] = '"1' + properties1['name']
        elif properties['chain'] == 'OUTPUT':
            # LITP automatically prefixes OUTPUT chain rule names with a 1
            if 'iniface' in properties:
                properties['name'] = '"10' + properties['name']
            else:
                properties['name'] = '"1' + properties['name']
        return properties, properties1

    def verify_fw_rules(self, node):
        """
        Description:
            Verify each Firewall rule is correctly represented in iptables or
            ip6tables or both. Verifies expected output by calling sub
            function _verify_iptables().
        Args:
            node (str): Node on which to verify firewall rules.
        Actions:
            a. Verify expected output from iptables/ip6tables commands.
        Results:
            True.
        """
        # a. Verify expected output from iptables
        if self.iptable_options['iptables']:
            for table in self.iptable_options['iptables']:
                if self.iptable_options['iptables'][table]:
                    self._verify_iptables(node,
                                  self.iptable_options['iptables'][table],
                                  self.IP_TABLES, table)

        # b. Verify expected output from ip6tables
        if self.iptable_options['ip6tables']:
            for table in self.iptable_options['ip6tables']:
                if self.iptable_options['ip6tables'][table]:
                    self._verify_iptables(node,
                                  self.iptable_options['ip6tables'][table],
                                  self.IP6_TABLES, table)

    def convert_litp_format_to_iptables_format(self, firewall_rules):
        """
        Description:
            Convert firewall rules from format found in LITP Model to that
            expected in iptables/ip6tables.
            Calls sub functions _process_fw_rule_properties() to process each
            rule and determine exactly the output expected in iptables and
            ip6tables.
        Args:
            firewall_rules (list): List of firewall-rule items taken from LITP
                                   model.
        Actions:
            a. Reset expected output
            b. For each firewall rule, process the LITP model properties and
               determine expected output from iptables/ip6tables commands.
        Results:
            True.
        """
        # a. Reset expected output to prevent hangover from last node checked.
        self.iptable_options = {'iptables': {'filter': [],
                                             'nat': [],
                                             'mangle': [],
                                             'raw': []},
                                'ip6tables': {'filter': [],
                                              'mangle': [],
                                              'raw': []}}
        # b. For each firewall rule, process the LITP model properties and
        #    determine expected output from iptables/ip6tables commands.
        for fw_rule in firewall_rules:
            props = self.get_props_from_url(self.ms_node, fw_rule)
            self.assertNotEqual([], props)

            self._process_fw_rule_properties(props)

    def get_list_fw_rules_to_verify(self, node):
        """
        Description:
            Get the list of all firewall rules which need to be verified for
            a node. Note this is only LITP user defined firewall rules, and
            as such, does not include default firewall rules.
            For a management server, all firewall rules are defined explicitly
            in the LITP model for that node.
            For a managed node, firewall rules for that node are a combination
            of those defined at node level and those defined at cluster level.
        Args:
            node (str): Node for which list of fw rules is required.
        Actions:
            a. If MS node, simply return the full list of fw rules for MS.
            b. If managed node, combine list of fw rules defined for node
               with those defined at cluster level.
               b1. Check if firewall rules defined for node.
               b2. Add node firewall rules to list of fw rules to verify
               b3. Check that node is part of cluster.
               b4. Check if firewall rules defined for cluster.
               b5. Add cluster firewall rules to list of fw rules to verify
        Returns:
            fw_rules (list): list of firewall-rule items to verify for node.
        """
        fw_rules = []

        if node is self.ms_node:
            # a. If MS node, simply return the full list of fw rules for MS.
            if self.model["ms"][0]["fw_rules"]:
                fw_rules.extend(self.model["ms"][0]["fw_rules"])
        else:
            # b. If managed node, combine list of fw rules defined for node
            # with those defined at cluster level.
            # b1. Check if firewall rules defined for node.
            all_nodes = self.model["nodes"][:]
            for stored_node in all_nodes:
                if node == stored_node["name"]:
                    if stored_node["fw_rules"]:
                        # b2. Add node rules to list of fw rules to verify
                        fw_rules.extend(stored_node["fw_rules"])

            all_clusters = self.model["clusters"][:]
            for cluster in all_clusters:
                nodes = self.find(self.ms_node, cluster['url'], "node")
                # b3. Check that node is part of cluster.
                if node in nodes:
                    # b4. Check if firewall rules defined for cluster.
                    if cluster["fw_rules"]:
                        # b5. Add cluster rules to list of fw rules to verify
                        fw_rules.extend(cluster["fw_rules"])

        return fw_rules

    @attr('all', 'revert', 'system_check', 'firewall', 'firewall_tc01')
    def test_01_p_verify_firewalls(self):
        """
        Description:
        Tests that Firewall Configuration is correctly implemented on
        Management Server and all Managed Nodes and Clusters.

        Item Types of interest are firewall-node-config and firewall-rule
        on MS and each node and firewall-cluster-config and firewall-rule at
        cluster level.

        Actions:
        a. Get all Firewall related data from LITP model for MS.
        b. If 'firewall-node-config' exists for MS:
           b1. Get the list of all firewall rules which need to be verified.
           b2. Convert each rule to expected iptables/ip6tables output.
           b3. Verify the iptables/ip6tables output.
           b4. Verify the iptables/ip6tables output also contains all default
               port information.
        c. If no 'firewall-node-config' exists for MS, skip test case.

        d. Get all Firewall related data from LITP model Managed nodes
           and cluster.
        e. Create a list of all managed nodes to iterate over.
        f. Examine Firewall configuration for all nodes:
           f1. Get the list of all firewall rules which need to be verified.
           f2. Convert each rule to expected iptables/ip6tables output.
           f3. Verify the iptables/ip6tables output.
           f4. Verify the iptables/ip6tables output also contains all default
               port information.
           f5. If No Firewall rules defined in LITP for MN or Cluster, but
               there is a 'firewall-node-config' item defined, simply verify
               default LITP Firewall rules are applied.
           f6. If No Firewall rules defined and no 'firewall-node-config' item
               defined, check if 'firewall-cluster-config' defined.
               - Default LITP Firewall rules should be applied.
               - iptables and ip6tables should be empty.
        Result:
        All firewall rules verified on MS and Managed nodes using iptables and
        ip6tables
        """

        # a. Get all Firewall related data from LITP model and store in
        #    data structures.
        firewall_node_config_exists = self.get_litp_ms_fw_config_data()

        # b. If 'firewall-node-config' exists for MS
        if firewall_node_config_exists:
            node = self.model["ms"][0]["name"]
            # b1. Get the list of all firewall rules which need to be verified.
            fw_rules_list = self.get_list_fw_rules_to_verify(node)
            if fw_rules_list:
                # b2. Convert each rule to expected iptables/ip6tables output.
                self.convert_litp_format_to_iptables_format(fw_rules_list)
                # b3. Verify the iptables/ip6tables output.
                self.verify_fw_rules(node)
            # b4. Verify the iptables/ip6tables output also contains all
            #     default port information.
            self.log('info', 'Verify Default LITP firewall rules on MS')
            self._verify_iptables_default_ports(node)
        else:
            self.log('info', 'Skip testing of MS as no firewall config exists')
            self.log('info', 'Nothing to verify on MS')

        # d. Get all Firewall related data from LITP model and store in
        #    data structures.
        self.get_litp_cluster_fw_config_data()
        self.get_litp_managed_node_fw_config_data()

        # e. Create a list of managed node items to iterate over.
        all_nodes = self.model["nodes"][:]

        # f. Examine Firewall configuration for all Nodes.
        for stored_node in all_nodes:
            node = stored_node["name"]
            # f1. Get the list of all firewall rules which need to be verified.
            fw_rules_list = self.get_list_fw_rules_to_verify(node)
            if fw_rules_list:
                # f2. Convert each rule to expected iptables/ip6tables output.
                self.convert_litp_format_to_iptables_format(fw_rules_list)
                # f3. Verify the iptables/ip6tables output.
                self.verify_fw_rules(node)
                # f4. Verify the iptables/ip6tables output also contains all
                #     default port information.
                self.log('info', node + ': Verify Default LITP firewalls')
                self._verify_iptables_default_ports(node)
            elif stored_node["fw_node_config"]:
                # f5.
                # If there are no fw rules, but there is 'firewall-node-config'
                # item, then iptables/ip6tables should contain default rules.
                self.log('info', node + ': Verify Default LITP firewalls')
                self._verify_iptables_default_ports(node)
            else:
                # f6.
                # If there are no fw rules and no 'firewall-node-config' item,
                # then iptables/ip6tables will be empty unless the
                # 'firewall-cluster-config' item is defined at cluster level
                all_clusters = self.model["clusters"][:]
                for cluster in all_clusters:
                    nodes = self.find(self.ms_node, cluster['url'], "node")
                    if node in nodes:
                        if cluster["fw_cluster_config"]:
                            self.log('info', 'Cluster level fw-cluster-config')
                            self.log('info', 'Verify Default LITP firewalls')
                            self._verify_iptables_default_ports(node)
                        else:
                            self.log('info', node + ' Empty iptables expected')
                            self.log('info', 'Nothing to verify on ' + node)
