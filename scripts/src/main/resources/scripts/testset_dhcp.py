"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     August 2015
@author:    Laura Forbes
"""

from litp_generic_test import GenericTest, attr


class Dhcp(GenericTest):
    """
    Test the 'dhcpservice_extension' LITP item type.
    Item Types verified are 'dhcp-service', 'dhcp-subnet', 'dhcp-range',
            'dhcp6-service', 'dhcp6-subnet' and 'dhcp6-range'.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(Dhcp, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])

        # Used for checking dhcp-service 'primary' property
        self.service_primary = None
        # Used for checking dhcp6-service 'primary' property
        self.service6_primary = None

    def tearDown(self):
        """ Teardown run after every test """

        super(Dhcp, self).tearDown()

    def _dhcp_service(self, service_path, dhcp_type, node_name):
        """
        Description:
            Tests that if dhcp-service or dhcp6-service 'primary' property is
                set to 'true', the other peer server's 'primary' property is
                    not also set to true since there is a dhc failover setup.
            Ensure that dhcpd is running on the node.

        Args:
            service_path (str): Path to dhcp-service or dhcp6-service
                                                item type in the model.
            dhcp_type (str): 'dhcp' (for dhcp-service) or
                                                'dhcp6' (for dhcp6-service).
            node_name (str): Name of the node being tested.

        Actions:
            a. Get the properties of the path.
            b. Check if the item is dhcp or dhcp6.
            c. If the 'primary' property is set to 'true', ensure the peer
                                server's 'primary' property is not also 'true'.
            d. If the 'primary' property is set to 'true', note this to ensure
                                the peer server is set to 'false'.
            e. Ensure that dhcpd is running on the node.
            f. Return dictionary containing service_name, primary,
                        domainsearch, nameservers and ntpservers properties.

        Returns:
            service_dict (dict): 'service_name', 'primary', 'domainsearch',
                    'nameservers' and 'ntpservers' property values.
        """
        # a. Get the properties of the path.
        service_props = self.get_props_from_url(self.ms_node, service_path)

        service_name = service_props['service_name']
        primary = service_props['primary']

        # The following properties are not always present:
        domainsearch = (service_props['domainsearch'] if 'domainsearch'
                                            in service_props else None)
        nameservers = (service_props['nameservers'] if 'nameservers'
                                            in service_props else None)
        ntpservers = (service_props['ntpservers'] if 'ntpservers'
                                            in service_props else None)

        # b. Check if the item is dhcp or dhcp6.
        serv_primary = None
        if dhcp_type == 'dhcp':
            serv_primary = self.service_primary
        elif dhcp_type == 'dhcp6':
            serv_primary = self.service6_primary

        # Ensure that only 1 dhcp-service and 1 dhcp6-service 'primary'
        # properties in the model are set to 'true' as a dhcp-service can have
        # exactly 1 primary and 1 secondary instances for failover.

        # c. If the 'primary' property is set to 'true' and the peer server's
        #   property has been tested, ensure it is not also 'true'.
        self.assertFalse(primary == 'true' and serv_primary,
            "dhcp-service: 'primary' properties in both {0} and {1} are set to"
                " 'true'.\nOnly 1 server can act as a primary server, as there"
                    " is a dhc failover setup in place.".format(
                serv_primary, service_path))

        # d. If the 'primary' property is set to 'true', note this to ensure
        #       the peer server is set to 'false'
        if primary == 'true' and serv_primary == self.service_primary:
            self.service_primary = service_path
        else:
            self.service6_primary = service_path

        # e. Ensure that dhcpd is active on the node
        self.get_service_status(node_name,
                                "dhcpd",
                                assert_running=True)

        # f. Return dictionary containing 'service_name', 'primary',
        #       'domainsearch', 'nameservers' and 'ntpservers' property values
        service_dict = {'service_name': service_name, 'primary': primary,
            'domainsearch': domainsearch, 'nameservers': nameservers,
            'ntpservers': ntpservers}

        return service_dict

    def _dhcp_subnet(self, subnet_path):
        """
        Description:
            Return the 'network_name' property of the path passed in.

        Args:
            subnet_path (str): Path to dhcp-subnet item type in the model.

        Actions:
            a. Get the properties of the path.
            b. Return the 'network_name' property value.

        Returns:
            The 'network_name' property value of the path passed in.
        """
        # a. Get the properties of the path
        subnet_props = self.get_props_from_url(self.ms_node, subnet_path)

        # b. Return the 'network_name' property value
        return subnet_props['network_name']

    def _dhcp_range(self, range_path):
        """
        Description:
            Return the 'start' and 'end' property values of the path passed in.

        Args:
            range_path (str): Path to dhcp-range item type in the model.

        Actions:
            a. Get the properties of the path.
            b. Return the 'start' and 'end' property values.

        Returns:
            Dictionary containing 'start' and 'end' properties.
        """
        # a. Get the properties of the path
        range_props = self.get_props_from_url(self.ms_node, range_path)

        # b. Return the 'start' and 'end' property values
        return {'start': range_props['start'], 'end': range_props['end']}

    @attr('all', 'revert', 'system_check', 'dhcp', 'dhcp_tc01')
    def test_01_p_dhcp(self):
        """
        Description:
            Tests that if dhcp-service or dhcp6-service 'primary' property is
                set to 'true', the other peer server's 'primary' property is
                    not also set to true since there is a dhc failover setup.
            If a dhcp-service or dhcp6-service item exists for a node,
                    ensure that dhcp is running on that node.

        Actions:
            For each node:
            For each dhcp type:
            1. dhcp-service
                a. Check for any modelled 'dhcp-service' or
                                    'dhcp6-service' items on node.
                For each dhcp-service/dhcp6-service path:
                b. Get dictionary of 'service_name', 'primary', 'domainsearch',
                        nameservers' and 'ntpservers' property values.
            2. dhcp-subnet
                a. Check for any modelled 'dhcp-subnet' or
                                    'dhcp6-subnet' items on node.
                For each dhcp-subnet/dhcp6-subnet path:
                b. Get the 'network_name' property.
            3. dhcp-range
                a. Check for any modelled 'dhcp-range' or
                                    'dhcp6-range' items on node.
                For each dhcp-range/dhcp6-range path:
                b. Get the 'start' and 'end' properties.
        """
        dhcp_types = ['dhcp', 'dhcp6']

        for node in self.all_nodes:
            node_name = node["name"]

            for dhcp_type in dhcp_types:
                # 1. dhcp-service
                # 1a. Check for any modelled 'dhcp-service' or
                #                   'dhcp6-service' items on node
                dhcp_service_paths = self.find(self.ms_node, node["url"],
                    "{0}-service".format(dhcp_type), assert_not_empty=False)

                # For each dhcp-service/dhcp6-service path:
                for service_path in dhcp_service_paths:
                    # 1b. Get dictionary of 'service_name',
                    #       'primary', 'domainsearch',
                    #           'nameservers' & 'ntpservers' property values
                    self._dhcp_service(
                        service_path, dhcp_type, node_name)

                # 2. dhcp-subnet
                # 2a. Check for any modelled 'dhcp-subnet' or
                #                   'dhcp6-subnet' items on node
                dhcp_subnet_paths = self.find(self.ms_node, node["url"],
                        "{0}-subnet".format(dhcp_type), assert_not_empty=False)

                # For each dhcp-subnet/dhcp6-subnet path:
                for subnet_path in dhcp_subnet_paths:
                    # 2b. Get the 'network_name' property
                    self._dhcp_subnet(subnet_path)

                # 3. dhcp-range
                # 3a. Check for any modelled 'dhcp-range' or
                #                   'dhcp6-range' items on node
                dhcp_range_paths = self.find(self.ms_node, node["url"],
                        "{0}-range".format(dhcp_type), assert_not_empty=False)

                # For each dhcp-range/dhcp6-range path:
                for range_path in dhcp_range_paths:
                    # 3b. Get the 'start' and 'end' properties
                    self._dhcp_range(range_path)
