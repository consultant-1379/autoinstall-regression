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
from networking_utils import NetworkingUtils
import test_constants
import re


class Network(GenericTest):
    """
    Test the Network LITP extension type.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(Network, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])
        self.net = NetworkingUtils()
        self.networks = self.find(self.ms_node, "/infrastructure", "network")

    def tearDown(self):
        """ Teardown run after every test """

        super(Network, self).tearDown()

    @staticmethod
    def format_file_config_to_dict(config):
        """
        Description:
            Function that returns a dictionary created from a list. The list
            must contain the lines of the eth config file.
        Args:
            config (list): A list of the contents of the eth config file.
            (/etc/sysconfig/network-scripts/ifcfg-X)
        Returns:
            dict.

            |   Example:
            |       {
            |           "device_name": "eth0"
            |           "macaddress": "52:54:00:00:54:52"
            |           "master": "bond_mgmt"
            |           "ipaddress": "10.10.10.100"
            |       }
        """
        r_dict = {}
        # a dict for mapping config file values to LITP properties.
        values = {"HWADDR": "macaddress", "BRIDGE": "bridge",
                  "MASTER": "master", "DEVICE": "device_name",
                  "IPADDR": "ipaddress", "IPV6ADDR": "ipv6address",
                  "DELAY": "forwarding_delay"}

        for line in config:
            if line[0].strip() == "#":
                continue

            # only split the line on the first "=" as bonding options will have
            # more than one
            line = line.split("=", 1)
            if line[0] in values:
                r_dict[values[line[0]]] = line[1].strip('"')

            # logic to deal with bonding options.
            # bonding options in the config are presented on one line separated
            # by spaces.
            if line[0] == "BONDING_OPTS" or line[0] == "BRIDGING_OPTS":
                line[1] = line[1].strip('"')
                opts = line[1].split(" ")
                for opt in opts:
                    opt = opt.split("=")
                    r_dict[opt[0]] = opt[1]
                continue

            # logic to handle bridge STP option
            if line[0] == "STP":
                line[1] = line[1].strip()
                if line[1] == "on":
                    r_dict["stp"] = "true"
                    continue
                r_dict["stp"] = "false"

        return r_dict

    def check_bonded_eth_mac(self, node, eth_props):
        """
        Description:
            Check the mac address of a bonded eth type.
            Checking for bonded eth type is different as mac address is not in
            /etc/sysconfig/network-scripts/ifcfg-X file but stored in
            /proc/net/bonding/X under the relavant bond. This function
            implements the logic to exract the required mac from this file.
        Args:
            eth_props (dict): A dictionary containing the LITP properties of
            the eth type.
        """
        # Get bond name
        path = "/proc/net/bonding/{0}".format(eth_props["master"])
        proc_file = self.get_file_contents(node, path, su_root=True)

        # Get the index of the line that starts the description of the required
        # eth (Slave Interface: ethX)
        idx = proc_file.index("Slave Interface: {0}"
                              .format(eth_props["device_name"]))

        # Search for the mac address in the remainder of the file.
        for line in proc_file[idx:]:
            if line.startswith("Permanent HW addr"):
                line = line.split(":", 1)
                line[1] = line[1].strip()
                self.assertEqual(line[1].lower(),
                                 eth_props["macaddress"].lower())
                # macaddress was now checked and can be removed to allow the
                # remaining properties to be verified
                del eth_props["macaddress"]
                break

    def get_genmask_from_litp_subnet(self, ip_mask):
        """
        Description:
            This function converts an IP address with slash notation bit length
            to an IP address and subnet mask.
            e.g. 192.168.0.1/24 will return  192.168.0.1, 255.255.255.0
        Args:
            mask (str): IP address with slash notation mask bit length.
            e.g 192.168.0.1/24
        Returns:
            tuple. A tuple with the first element being the IP address and the
            second element containing the subnet mask.
            e.g ("192.168.0.1", "255.255.255.0")
        """
        cmd = "/bin/ipcalc -m {0}".format(ip_mask)
        netmask, std_err, rc = self.run_command_local(cmd)
        self.assertEqual(0, rc)
        self.assertEqual([], std_err)

        netmask = netmask[0].split("=")[1]
        ip_addr = ip_mask.split("/")[0]

        return ip_addr, netmask

    def check_network_subnet(self, item_props):
        """
            Description:
                Compare the subnet of the network item and
                ipaddress of item passed only if they have the same
                name property
        """
        self.log("info", "Check Ip address is in subnet range for {0}"\
                                .format(item_props['network_name']))
        for network in self.networks:
            network_props = self.get_props_from_url(self.ms_node, network)
            if item_props['network_name'] == network_props['name']:
                if "subnet" in network_props:
                    subnet = network_props['subnet'].split("/")
                    # network_props['subnet'] = "aaa.bbb.ccc.ddd/mask"
                    # subnet = ["aaa.bbb.ccc.ddd"]["mask"]
                    # Example: ip = 192.168.x.y
                    #    mask=26 | 192.168.x.y~y+62 | subnet_mask = 3
                    #    mask=24 | 192.168.x.0~254 | subnet_mask = 3
                    #    mask=18 | 192.168.x~x+63.0~254 | subnet_mask = 2
                    #    mask=16 | 192.168.0~255.0~254 | subnet_mask = 2
                    #    mask= 8 | 192.0~255.0~255.0~254 | subnet_mask = 1
                    subnet_mask = int(subnet[1]) / 8
                    mask_rest = int(subnet[1]) % 8
                    subnet_ip = subnet[0].split(".")
                    item_ip = item_props['ipaddress'].split(".")
                    for range_n in range(len(item_ip)):
                        # Assert IP part equals subnet part
                        if range_n < subnet_mask:
                            self.assertEqual(subnet_ip[range_n], \
                                                item_ip[range_n])
                        else:
                            # Empty mask part
                            if mask_rest == 0 or range_n > subnet_mask:
                                if range_n < 3:
                                    self.assertTrue(
                                        (int(item_ip[range_n]) >= 0) and
                                        (int(item_ip[range_n]) <= 255))
                                else:
                                    self.assertTrue(
                                        (int(item_ip[range_n]) >= 1) and
                                        (int(item_ip[range_n]) <= 254))
                            else:
                                # If mask part doesn't cover all ip part
                                subnet_mask_range = 2 ** (8 - mask_rest) - 2
                                if range_n < 3:
                                    self.assertTrue(
                                        int((item_ip[range_n]) >=
                                            int(subnet_ip[range_n])) and
                                        (int(item_ip[range_n]) <=
                                         (int(subnet_ip[range_n]) +
                                          int(subnet_mask_range) + 1)))
                                else:
                                    # Last IP part with mask
                                    self.assertTrue(
                                        (int(item_ip[range_n]) >=
                                         int(subnet_ip[range_n])) and
                                        (int(item_ip[range_n]) <=
                                            (int(subnet_ip[range_n]) +
                                             int(subnet_mask_range) + 1)))
                    self.log("info", "Ip address is in subnet range for {0}"
                             .format(item_props['network_name']))
                    break
        else:
            self.log("info", "No subnet for {0} ip address"
                     .format(item_props['network_name']))

    def check_bridge_interface(self, node, bridge, interface):
        """
        Description:
            This function verifys if an interface belonging to a bridge is
            listed under that bridge.
        Args:
            bridge (str): Name of the brige to check.
            interface (str): Name of the interface to check.
        """
        cmd = "/usr/sbin/brctl show {0} | grep {1}$".format(bridge, interface)
        std_out, std_err, rc = self.run_command(node, cmd)
        self.assertNotEqual([], std_out)
        self.assertEqual(0, rc)
        self.assertEqual([], std_err)

    @attr('all', 'revert', 'system_check', 'network', 'network_tc01')
    def test_01_p_check_eth_type(self):
        """
        Description:
            Test the 'eth' LITP item type.
            Verify that any eth types in the LITP model are configured on
            the corresponding node/ms.
        Actions:
            1. For each node:
                a. Get all eth types defined
                b. For each eth type found:
                    b1. Get all the properties of the eth
                    b2. Get config file for eth device.
                    b3. Format config into dictionary for easy comparison.
                    b4. Check if the eth belongs to a bond
                    b5. Verify LITP properties match the config file dict.
                    b6. Check that the eth is UP
                    b7. Check if the eth belongs to a bridge.
        """

        # 1. For each node
        for node in self.all_nodes:
            # a. Get all eth types defined on this node
            eth_urls = self.find(self.ms_node, node["url"], "eth")

            # b. For each eth:
            for eth in eth_urls:
                self.log("info", "Checking eth {0}".format(eth))
                # b1. Get all the properties of the eth
                eth_props = self.get_props_from_url(self.ms_node, eth)

                # b2. Get config file for eth device.
                file_path = "{0}/ifcfg-{1}"\
                    .format(test_constants.NETWORK_SCRIPTS_DIR,
                            eth_props["device_name"])
                config = self.get_file_contents(node["name"], file_path,
                                                su_root=True)

                # b3. Format config into dictionary for easy comparison.
                config = self.format_file_config_to_dict(config)

                # b4. Check if the eth belongs to a bond
                #     If the eth is part of a bond then the mac address will
                #     not be in the config. Must be checked in another file.
                self.log("info", "Checking if eth: {0} belongs to a bond."
                         .format(eth_props["device_name"]))
                if "master" in eth_props:
                    self.check_bonded_eth_mac(node['name'], eth_props)

                # b5. Verify LITP properties match the config file dict.
                for item in eth_props:
                    if item == "ipaddress":
                        self.check_network_subnet(eth_props)
                    # skip the "network_name" property as it's specific to LITP
                    if item == "network_name":
                        continue
                    # Check the config contains LITP property
                    self.log("info", "Verify '{0}' property".format(item))
                    self.assertTrue(item in config)
                    # Check the properties match
                    self.assertEqual(eth_props[item], config[item])

                # b6. Check that the eth is UP
                cmd = "/sbin/ip link | grep -E '{0}.*UP'"\
                      .format(eth_props["device_name"])
                self.log("info", "Checking if eth: {0} is UP."
                         .format(eth_props["device_name"]))
                std_out, _, _ = self.run_command(node["name"], cmd,
                                                 su_root=True)
                self.assertNotEqual([], std_out)

                # b7. Check if the eth belongs to a bridge.
                self.log("info", "Checking if eth: {0} belongs to a bridge."
                         .format(eth_props["device_name"]))
                if "bridge" in eth_props:
                    self.check_bridge_interface(node["name"],
                                                eth_props["bridge"],
                                                eth_props["device_name"])

    @attr('all', 'revert', 'system_check', 'network', 'network_tc02')
    def test_02_p_check_bond_type(self):
        """
        Description:
            Test the 'bond' LITP item type.
            Verify that any bond types in the LITP model are configured on
            the corresponding node/ms.
        Actions:
            1. For each node:
                a. Get all bond types defined
                b. For each bond type found:
                    b1. Get all bond properties
                    b2. Get config file for bond device.
                    b3. Format config into dictionary for easy comparison.
                    b4. Verify LITP properties match the config file dict.
                    b5. Check that the bond is UP.
                    b6. Check if the bond belongs to a bridge.
        """
        for node in self.all_nodes:
            # a. Get all bond types defined on this node
            bond_urls = self.find(self.ms_node, node["url"], "bond",
                                  assert_not_empty=False)

            for bond in bond_urls:
                self.log("info", "Checking bond {0}".format(bond))
                # b1. Get all bond properties
                bond_props = self.get_props_from_url(self.ms_node, bond)

                # b2. Get config file for bond device.
                file_path = "{0}/ifcfg-{1}"\
                    .format(test_constants.NETWORK_SCRIPTS_DIR,
                            bond_props["device_name"])
                config = self.get_file_contents(node["name"], file_path,
                                                su_root=True)

                # b3. Format config into dictionary for easy comparison.
                config = self.format_file_config_to_dict(config)

                # b4. Verify LITP properties match the config file dict.
                for item in bond_props:
                    if item == "ipaddress":
                        self.check_network_subnet(bond_props)
                    # skip the "network_name" property as it's specific to LITP
                    if item == "network_name":
                        continue
                    self.log("info", "Verify '{0}' property".format(item))
                    # Check the config contains LITP property
                    self.assertTrue(item in config)
                    # Check the properties match
                    self.assertEqual(bond_props[item], config[item])

                # b5. Check that the bond is UP
                self.log("info", "Checking if bond: {0} is UP."
                         .format(bond_props["device_name"]))
                cmd = "/sbin/ip link | grep -E ' {0}:' | grep -E 'UP'"\
                      .format(bond_props["device_name"])
                std_out, _, _ = self.run_command(node["name"], cmd,
                                                 su_root=True)
                self.assertNotEqual([], std_out)

                # b6. Check if the bond belongs to a bridge.
                self.log("info", "Checking if bond: {0} belongs to a bridge."
                         .format(bond_props["device_name"]))
                if "bridge" in bond_props:
                    self.check_bridge_interface(node["name"],
                                                bond_props["bridge"],
                                                bond_props["device_name"])

    @attr('all', 'revert', 'system_check', 'network', 'network_tc03')
    def test_03_p_check_bridge_type(self):
        """
        Description:
            Test the 'bridge' LITP item type.
            Verify that any bridge types defined in the LITP model are
            configured correctly on the corresponding node/ms.
        Actions:
            1. For each node:
                a. Get all bridge types defined
                b. For each bridge type found:
                    b1. Get all bridge properties
                    b2. Get config file for bridge device.
                    b3. Format config into dictionary for easy comparison.
                    b4. Verify LITP properties match the config file dict.
                    b5. Check the bridge is UP.
        """
        for node in self.all_nodes:
            # a. Get all bridge types defined on this node
            bridge_urls = self.find(self.ms_node, node["url"], "bridge",
                                    assert_not_empty=False)

            for bridge in bridge_urls:

                # b1. Get all bridge properties
                bridge_props = self.get_props_from_url(self.ms_node, bridge)

                # b2. Get config file for bridge device.
                file_path = "{0}/ifcfg-{1}"\
                    .format(test_constants.NETWORK_SCRIPTS_DIR,
                            bridge_props["device_name"])
                config = self.get_file_contents(node["name"], file_path,
                                                su_root=True)

                # b3. Format config into dictionary for easy comparison.
                config = self.format_file_config_to_dict(config)

                # b4. Verify LITP properties match the config file dict.
                for item in bridge_props:
                    if item == "ipaddress":
                        self.check_network_subnet(bridge_props)
                    # skip the "network_name" property as it's specific to LITP
                    if item == "network_name":
                        continue
                    self.log("info", "Verify '{0}' property".format(item))
                    # Check the config contains LITP property
                    self.assertTrue(item in config)
                    # Check the properties match
                    self.assertEqual(bridge_props[item], config[item])

                # b5. Check the bridge is UP
                self.log("info", "Checking if bridge: {0} is UP."
                         .format(bridge_props["device_name"]))
                cmd = "/sbin/ip link | grep -E ' {0}:' | grep -E 'UP'"\
                      .format(bridge_props["device_name"])
                std_out, _, _ = self.run_command(node["name"], cmd,
                                                 su_root=True)
                self.assertNotEqual([], std_out)

    @attr('all', 'revert', 'system_check', 'network', 'network_tc04')
    def test_04_p_check_route_type(self):
        """
        Description:
            Test the 'route' LITP item type.
            Verify that any route types defined in the LITP model are
            configured correctly on the corresponding node/ms.
        Actions:
            1. For each node:
                a. Get all route types defined
                b. Get the ip routing tables for the node
                c. For each route type found:
                    c1. Get all route properties
                    c2. Verify LITP properties match the config.
        """
        for node in self.all_nodes:
            # a. Get all route types defined on this node
            route_urls = self.find(self.ms_node, node["url"], "route",
                                   assert_not_empty=False)

            # b. Get the ip routing tables for the node
            cmd = self.net.get_route_cmd("-n")
            config, std_err, rc = self.run_command(node["name"], cmd)
            self.assertEqual(0, rc)
            self.assertEqual([], std_err)

            for route in route_urls:
                # c1. Get all route properties
                route_props = self.get_props_from_url(self.ms_node, route)

                # c2. Verify LITP properties match the IP routing table
                self.log("info", "Verify the route is in the IP routing table")
                dest, genmask = \
                    self.get_genmask_from_litp_subnet(route_props["subnet"])

                # regex of format "Destination Gateway Genmask"
                regex = "{0} *{1} *{2}"\
                        .format(dest, route_props["gateway"], genmask)
                self.assertTrue(any(re.search(regex, x) for x in config))

    @attr('all', 'revert', 'system_check', 'network', 'network_tc05')
    def test_05_p_check_route6_type(self):
        """
        Description:
            Test the 'route6' LITP item type.
            Verify that any route6 types defined in the LITP model are
            configured correctly on the corresponding node/ms.
        Actions:
            1. For each node:
                a. Get all route6 types defined
                b. Get the ip6 routing tables for the node
                c. For each route6 type found:
                    c1. Get all route6 properties
                    c2. Verify LITP properties match the config.
        """
        pattern = re.compile(r'(:*)0+([1-9a-f]*)(:*)')
        for node in self.all_nodes:
            # a. Get all route6 types defined on this node
            route_urls = self.find(self.ms_node, node["url"], "route6",
                                   assert_not_empty=False)

            # b. Get the ip routing tables for the node
            cmd = self.net.get_route_cmd("-A inet6 -n")
            config, std_err, rc = self.run_command(node["name"], cmd)
            self.assertEqual(0, rc)
            self.assertEqual([], std_err)

            for route6 in route_urls:
                # c1. Get all route6 properties
                route6_props = self.get_props_from_url(self.ms_node, route6)

                # c2. Verify LITP properties match the IP6 routing table
                self.log("info",
                         "Veriy the route6 is in the IP6 routing table")

                # regex of format "Destination Gateway Genmask"
                regex = "{0} *{1}".format(
                    pattern.sub(r'\1\2\3', route6_props["subnet"]).
                        replace(':', ''),
                    pattern.sub(r'\1\2\3', route6_props["gateway"]).
                        replace(':', ''))
                self.assertTrue(
                    any(re.search(regex,
                                  pattern.sub(r'\1\2\3', x).replace(':', ''))
                        for x in config))

    @attr('all', 'revert', 'system_check', 'network', 'network_tc06')
    def test_06_p_check_vlan_type(self):
        """
        Description:
            Test the 'vlan' LITP item type.
            Verify that any vlan types defined in the LITP model are
            configured correctly on the corresponding node/ms.
        Actions:
            1. For each node:
                a. Get all vlan types defined
                b. For each vlan type found:
                    b1. Get all vlan properties
                    b2. Get the config for the vlan
                    b3. Format the config to dict
                    b4. Verify the properties of the vlan match the config.
                    b5. Check if the vlan belongs to a bridge.
        """
        for node in self.all_nodes:
            # a. Get all vlan types defined on this node
            vlan_urls = self.find(self.ms_node, node["url"], "vlan",
                                  assert_not_empty=False)

            # b. For each vlan type found:
            for vlan in vlan_urls:
                # b1. Get all vlan properties
                vlan_props = self.get_props_from_url(self.ms_node, vlan)

                # b2. Get config file for vlan device.
                file_path = "{0}/ifcfg-{1}"\
                    .format(test_constants.NETWORK_SCRIPTS_DIR,
                            vlan_props["device_name"])
                config = self.get_file_contents(node["name"], file_path,
                                                su_root=True)

                # b3. Format config into dictionary for easy comparison.
                config = self.format_file_config_to_dict(config)

                # b4. Verify the properties of the vlan match the config.
                for item in vlan_props:
                    if item == "ipaddress":
                        self.check_network_subnet(vlan_props)
                    # skip the "network_name" property as it's specific to LITP
                    if item == "network_name":
                        continue
                    self.log("info", "Verify '{0}' property".format(item))
                    # Check the config contains LITP property
                    self.assertTrue(item in config)
                    # Check the properties match
                    self.assertEqual(vlan_props[item], config[item])

                # b5. Check the vlan is up
                self.log("info", "Checking if vlan: {0} is UP."
                         .format(vlan_props["device_name"]))
                cmd = "/sbin/ip link | grep -E ' {0}@' | grep -E 'UP'"\
                      .format(vlan_props["device_name"])
                std_out, _, _ = self.run_command(node["name"], cmd,
                                                 su_root=True)
                self.assertNotEqual([], std_out)

                # b6. Check if the vlan belongs to a bridge.
                self.log("info", "Checking if vlan: {0} belongs to a bridge."
                         .format(vlan_props["device_name"]))
                if "bridge" in vlan_props:
                    self.check_bridge_interface(node["name"],
                                                vlan_props["bridge"],
                                                vlan_props["device_name"])
