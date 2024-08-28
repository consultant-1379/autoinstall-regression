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
import socket


class NetworkTimeProtocol(GenericTest):
    """
    Test the Network Time Protocol in LITP.
    Item Types verified are 'ntp-server' and 'ntp-service'
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(NetworkTimeProtocol, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])
        self.ntp_stat_cmd = "/usr/bin/ntpstat"
        self.ntpq_cmd = "/usr/sbin/ntpq -pn"
        # 15 minutes should be sufficient
        self.ntp_timeout = 15

    def tearDown(self):
        """ Teardown run after every test """

        super(NetworkTimeProtocol, self).tearDown()

    @staticmethod
    def _is_ipaddress(server_name):
        """
        Description:
            Check if the server name matches an ip address format.
            The ntp server in the LITP Model could be an Ip Address or
            a hostname/alias.
            Check needed as it may be an alias in the LITP Model.
            If an alias, another item type needs to be checked to determine
            the actual ip address.

        Args:
            server_name

        Actions:
            a. Check if ipv4 address.
            b. Check if ipv6 address.

        Returns:
            True: if an ip address.
            False: if not an ip address.
        """
        # a. Check if ipv4 address
        try:
            socket.inet_aton(server_name)
            result = True
        except socket.error:
            result = False

        if not result:
            # b. Check if ipv6 address
            try:
                socket.inet_pton(socket.AF_INET6, server_name)
                result = True
            except socket.error:
                result = False

        return result

    def _get_ms_management_network_ipaddress(self):
        """
        Description:
            Get the Ipaddress of the MS on the Management Network from LITP.
            This is needed to verify the /etc/ntp.conf file on each Managed
            node has the correct ipaddress of the MS.
        Args:
            None
        Actions:
            a. Get Management Network name.
            b. For each interface defined in LITP model, check if on mgmt
               network.
               b1. If mgmt network and ipaddress defined, return ipaddress.
        Returns:
            ms_ip_address : IP Address of MS on Management Network.
        """
        network_name = self.get_management_network_name(self.ms_node)

        interfaces = self.find_children_of_collect(self.ms_node,
                                               '/ms/network_interfaces',
                                               "network-interface")

        ms_ip_found = False
        for interface in interfaces:
            props = self.get_props_from_url(self.ms_node, interface)
            if "network_name" in props:
                if network_name == props["network_name"] and \
                                   "ipaddress" in props:
                    ms_ip_address = props["ipaddress"]
                    ms_ip_found = True
                    break

        self.assertTrue(ms_ip_found, "IP Address of MS mgmt net not found")

        return ms_ip_address

    def _verify_ntp_config_file(self, node, file_contents, server, all_ms_ips,
                                is_ms=True):
        """
        Description:
            Verify that a nodes /etc/ntp.conf file contains the ntp-server.

        Args:
            node (str): node

            file_contents: contents of nodes /etc/ntp.conf file.

            server (str): ntp server expected to be in /etc/conf file.

            all_ms_ips (list): A list of all IP addresses configured on the MS

        Kwargs:
            is_ms (bool): Boolean to change behaviour if node is not an MS -
             Default is True.

        Actions:
            a. Verify that "server <ntp-server>" is in /etc/ntp.conf.

        Returns: -
        """
        file_to_check = test_constants.NTPD_CFG_FILE
        expected = "server " + server
        self.log("info", node["name"] +
                 ": Verifying '" + expected +
                 "' found in " + file_to_check)

        # Check if this node is the ms
        if is_ms:
            self.assertTrue(
                any(("#" not in line and expected in line)
                    for line in file_contents),
                expected + " not found in " + file_to_check + " file"
            )
        else:
            # This is a peer node so all MS ip addresses should be listed in
            # the config.
            for ms_ip in all_ms_ips:
                self.assertTrue(
                    any(("#" not in line and ms_ip in line)
                        for line in file_contents),
                    ms_ip + ": IP not found in " + file_to_check + " file"
                )

        server_found = False
        for line in file_contents:
            # Ignore commented out lines.
            if "#" not in line and expected in line:
                server_found = True
                break

        self.assertTrue(server_found, expected + " not found in " +
                                      file_to_check + " file")

    def _get_ntpalias_ipaddress(self, server):
        """
        Description:
            Get the actual ip address of the NTP server when an alias
            is used in LITP Model.
            E.G. server: ntpAlias1

        Args:
            server (str): ntp server alias name.

        Actions:
            a. Get all 'alias' item types from LITP Model.
            b. Find 'alias' item with 'alias_name' property set to the
               same as ntp server.
            c. Get 'address' property from 'alias' item.

        Returns:
            serverip (str): IP Address of NTP server.
        """
        aliases = self.find_children_of_collect(self.ms_node,
                                                '/ms/configs',
                                                "alias")

        server_found = False
        for alias in aliases:
            props = self.get_props_from_url(self.ms_node, alias)
            if "address" in props:
                if server in props["alias_names"]:
                    serverip = props["address"]
                    server_found = True
                    break

        self.assertTrue(server_found, "Server Not Found")
        return serverip

    def _verify_sync_with_correct_ntpserver(self, node, ntp_server,
                                            all_ms_ips, is_ms=True):
        """
        Description:
            Verify that a node is synchronised with the correct NTP server
            as defined in LITP model.

        Args:
            node (str): node to verify.

            ntp_server (str): ntp server which should be used.

            all_ms_ips (list): A list of all IP addresses configured on the MS

        Kwargs:
            is_ms (bool): Boolean to change behaviour if node is not an MS -
             Default is True.

        Actions:
            a. Execute 'ntpq -pn' command towards node.
            b. Verify that output contains: *<serverip> indicating server used
               for synchronisation.
               $ ntpq -pn
                    remote           refid      st t when poll reach   delay
               =============================================================
               *172.16.30.1     159.107.173.12   4 u  195  512  377    0.724

        Returns: -
        """
        cmd = self.ntpq_cmd

        if not self._is_ipaddress(ntp_server):
            # Get actual ntp server ip address rather than alias
            ntp_server = self._get_ntpalias_ipaddress(ntp_server)

        std_out, std_err, rc = self.run_command(node["name"], cmd,
                                                su_root=True)

        self.assertEquals([], std_err)
        self.assertNotEqual([], std_out)
        self.assertEquals(0, rc)

        if is_ms:
            self.log("info", node["name"] +
                     ": Verifying sync with ntp-server: " + ntp_server)

            server_to_use_as_sync = False
            for line in std_out:
                if ('*' in line or '+' in line) and ntp_server in line:
                    server_to_use_as_sync = True
                    break

            self.assertTrue(server_to_use_as_sync, node["name"] +
                            " not synced to ntp-server defined in LITP model")
        else:
            self.log("info", node["name"] +
                     ": Verifying peer node in sync with MS: " +
                     ntp_server)

            # Check that each ip on the MS is listed and one of the ips is the
            # ntp source.
            for ip_addr in all_ms_ips:
                self.assertTrue(any(ip_addr in line for line in std_out))

            for line in std_out:
                if '*' in line:
                    line = line.strip('*')
                    line = line.split(' ')[0]
                    self.assertTrue(line in all_ms_ips)
                    break

    def _get_all_ms_ips(self):
        """
        Description:
            Method to get all ip addresses configured on the MS.
        Returns:
            list of ip addresses.
        """
        std_out, std_err, rc = self.execute_cli_show_cmd(
            self.ms_node, '/ms/network_interfaces/', args='-r')

        self.assertEquals([], std_err)
        self.assertNotEqual([], std_out)
        self.assertEquals(0, rc)

        ret_ips = []
        for ip_addr in std_out:
            if 'ipaddress:' in ip_addr:
                ret_ips.append(ip_addr.split(' ')[1])

        return ret_ips

    @attr('all', 'revert', 'system_check', 'networktimeprotocol',
          'networktimeprotocol_tc01')
    def test_01_p_verify_ntp(self):
        """
        Description:
            Test the 'ntp-service' and 'ntp-server' LITP item types.
            Verify that MS and Peer Nodes are synchronised and to the
            correct NTP Server.

        Actions:
            1. Determine MS Ip Address.
            2. Find modelled 'ntp-service' item.
            3. Verify that the ntpd is running.
            4. Execute 'cat /etc/ntp.conf' command on node
            5. Verify that node is synchronised (ntpstat).
            if MS:
                6. Find all modelled 'ntp-server' items.
                7. Get all 'ntp-server' properties
                8. Verify 'ntp-server' is in nodes ntpd config file
                9. Get Primary NTP Server from LITP Model
                10. Verify node synched with correct 'ntp-server' (ntpq -pn).
            if Managed Node:
                11. Verify node synched with MS (ntpq -pn).
                12. Verify MS is in nodes ntp.conf file

        """
        # 1. Need to acquire ms ipaddress in order to verify ntpd config
        #    files on Managed nodes.
        ms_ip_address = self._get_ms_management_network_ipaddress()
        all_ms_ips = self._get_all_ms_ips()

        for node in self.all_nodes:
            # 2. Find modelled 'ntp-service' item.
            ntp_service = self.find(self.ms_node, node["url"],
                                    "ntp-service", assert_not_empty=False)

            if not ntp_service:
                self.log("info", node["name"] + ": No 'ntp-service' defined")
                continue

            # 3. Verify that the ntpd is running.
            self.log("info", node["name"] + ": Verifying ntpd is running")
            self.get_service_status(node["name"], 'ntpd')

            # 4. Execute 'cat /etc/ntp.conf' command on desired node.
            file_to_check = test_constants.NTPD_CFG_FILE
            self.log("info", node["name"] + ": cat /etc/ntp.conf file")
            file_contents = self.get_file_contents(node["name"],
                                                   file_to_check)

            # 5. Run 'ntpstat' command on the node
            # Regardless of configuration, we should check sync.
            self.log("info", node["name"] + ": Verifying node is Synchronised")

            # Wait for Nodes to be synchronised.
            self.assertTrue(
                self.wait_for_cmd(node["name"],
                                  self.ntp_stat_cmd,
                                  0,
                                  timeout_mins=self.ntp_timeout),
                node["name"] + " is not synchronised")

            if node["name"] == self.ms_node:
                # 6. Find all modelled 'ntp-server' items.
                ntp_servers = self.find(self.ms_node,
                                        ntp_service[0],
                                        "ntp-server",
                                        assert_not_empty=False)

                if not ntp_servers:
                    self.log("info", node["name"] +
                             ": No 'ntp-server' defined")
                    continue

                for ntp_server in ntp_servers:
                    # 7. Get all 'ntp-server' properties
                    props = self.get_props_from_url(self.ms_node,
                                                    ntp_server)

                    server = props["server"]

                    # 8. Verify 'ntp-server' is in nodes ntp.conf file
                    self._verify_ntp_config_file(node,
                                                 file_contents,
                                                 server,
                                                 all_ms_ips)

                # 9. Get Primary NTP Server from LITP Model
                primary_ntp_server = \
                    self.get_props_from_url(self.ms_node,
                                            ntp_servers[0],
                                            'server')

                # 10. Verify node synched with correct NTP server
                self._verify_sync_with_correct_ntpserver(
                    node, primary_ntp_server, all_ms_ips)
            else:
                # 11. Verify Managed Node is synched with the MS
                self._verify_sync_with_correct_ntpserver(node,
                                                         ms_ip_address,
                                                         all_ms_ips,
                                                         is_ms=False)

                # 12. Verify MS is in nodes ntp.conf file
                self._verify_ntp_config_file(node,
                                             file_contents,
                                             ms_ip_address,
                                             all_ms_ips,
                                             is_ms=False)
