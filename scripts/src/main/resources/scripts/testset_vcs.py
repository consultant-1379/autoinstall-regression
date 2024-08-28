"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     July 2015
@author:    James Langan, Brian Carey, Marco Gibboni
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from vcs_utils import VCSUtils


class VCS(GenericTest):
    """
    Test the VCS functionality in LITP.
    Item Types verified are 'vcs-cluster', 'vcs-network-host, 'disk',
    'storage-profile' and 'vcs-clustered-service'.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(VCS, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.rhc = RHCmdUtils()
        self.vcs = VCSUtils()

        # list of configuration files paths
        self.files_paths = ['/etc/sysconfig/llt', '/etc/sysconfig/gab',
                            '/etc/llthosts', '/etc/llttab', '/etc/gabtab']

        self.disk_props = sorted(['bootable',
                                  'disk_part',
                                  'name',
                                  'size',
                                  'uuid'])

    def tearDown(self):
        """ Teardown run after every test """

        super(VCS, self).tearDown()

    @staticmethod
    def get_vxfenconfig_cmd(args=""):
        """Returns a command to run a vxfenconfig cmd

        Args:
            args (str): arguments to be appended to the cmd.

        Returns:
            str. A command to return
            "/sbin/vxfenconfig [arguments]"
        """
        return "/sbin/vxfenconfig {0}".format(args)

    @staticmethod
    def parse_fencing_disk_config_list_for_uuids(vxfenconfig_output):
        """
        Function to parse through the output of a vxfenconfig -l command
        and return a list of the uuids found.

        Args:
           vxfenconfig_output (list): The output from a vxfenconfig -l command.

        Returns:
        list. A list of the uuids of the fencing disks created on the node."
        """
        uuids = []
        for line in vxfenconfig_output:
            split_lines = line.split(' ')
            if split_lines[0] == "/":
                items = [x for x in split_lines if x != '']
                uuids.append(items[3])
        uuids = uuids.sort()
        return uuids

    def get_vcs_model_info(self):
        """
        Function that returns a dictionary all the vcs clustered service
        information from the LITP model
        """

        service_groups = []

        multi_type_list = ['ha-service-config', 'vip', 'package',
                           'file-system', 'service', 'lsb-runtime']
        prop_dict = {}
        service_group = {}

        for cluster in self.model['clusters']:

            clus_servs = self.find(self.ms_node, cluster['url'],
                                   'vcs-clustered-service',
                                   assert_not_empty=False)
            for serv in clus_servs:
                # Check if this clustered service is a vm service
                vm_service = self.find(self.ms_node, serv, 'vm-service',
                                  assert_not_empty=False)
                # Ignore if VM service as it's tested in testset_vcs_vm.py
                if vm_service:
                    continue

                prop_dict['url'] = serv

                props = self.get_props_from_url(self.ms_node, serv)

                for prop in props:
                    prop_dict[prop] = props[prop]

                service_group['vcs-clustered-service'] = prop_dict

                prop_dict = {}

                for itype in multi_type_list:
                    urls = self.find(self.ms_node, serv, itype,
                                     assert_not_empty=False)
                    for url in urls:
                        props = self.get_props_from_url(self.ms_node, url)
                        prop_dict['url'] = url
                        for prop in props:
                            prop_dict[prop] = props[prop]

                        if itype in service_group:
                            service_group[itype].append(prop_dict)
                        else:
                            service_group[itype] = []
                            service_group[itype].append(prop_dict)
                        prop_dict = {}

                service_groups.append(service_group)
                service_group = {}

        self.log("info", "Printing dict from get_vcs_model_info()")
        self._print_list(0, service_groups)
        self.log("info", "Finished printing dict")

        return service_groups

    def verify_split_brain_protection(self, vcs_nodes, num_disks,
                                      uuid_specified_list):
        """
            VERIFY THE SPLIT BRAIN CONFIGURATION ON THE NODES IN THE CLUSTER
            IF 0 DISKS WERE ALLOCATED THEN AN ERROR MESSAGE OF 0 ACTIVE
            COORDINATION POINTS SHOULD BE RETURNED, OTHERWISE ENSURE THAT
            THE UUIDS CONFIGURED ON THE NODE MATCH THAT OF THOSE SPECIFIED.
        """
        for node in vcs_nodes:

            cmd = self.get_vxfenconfig_cmd("-l")

            stdout, stderr, returnc = self.run_command(node, cmd, su_root=True)

            if num_disks == 0:
                self.assertEqual(1, returnc)
                self.assertEqual("There are 0 active coordination points for "
                                 "this node", stdout[0])
                self.assertEqual([], stderr)

            else:
                self.assertEqual(0, returnc)
                self.assertEqual([], stderr)
                self.assertNotEqual([], stdout)

                node_uuids = \
                    self.parse_fencing_disk_config_list_for_uuids(stdout)

                self.assertEqual(uuid_specified_list, node_uuids)

    def get_res_state_per_node(self, node_filename, resource_name):
        """
        Return VCS resource state on the specified node

        @arg (str) node_filename  The node where to run the hares command
        @arg (str) resource_name  Name of the resource
        @ret (dict) Status of the given resource per node
        """
        cmd = self.vcs.get_hares_state_cmd() + resource_name
        stdout, stderr, rc = self.run_command(node_filename,
                                              cmd, su_root=True)
        self.assertEqual(0, rc)
        self.assertEqual([], stderr)

        return self.vcs.get_resource_state(stdout)

    def compare_disk_props(self, props_list):
        """
            This function compares the expected
            properties with the list name
            passed as parameter
        """
        for key in range(0, len(self.disk_props)):

            if self.disk_props[key] != props_list[key]:

                self.log('info', "The property '{0}' is missing!"
                         .format(self.disk_props[key]))

                return False

        return True

    def _verify_fencing_disks(self, cluster_url, cluster_id, cluster_type,
                              vcs_nodes):
        """
            Description:
                Verify fencing disk items in vcs-cluster
        """

        # Verify fencing disks and split brain protection.
        fen_disk_urls = self.find(self.ms_node, cluster_url +
                                  '/fencing_disks', "disk",
                                  assert_not_empty=False)

        num_disks = len(fen_disk_urls)

        allowed_num_disks = [0, 3]

        self.assertTrue(num_disks in allowed_num_disks)

        # Check to ensure that if the cluster type is not 'sfha', that no
        # fencing disks are then allocated
        if cluster_type != "sfha":

            self.assertEqual(0, num_disks)

        self.log("info", "Cluster Type: " + cluster_type +
                 ", Number of Fencing disks: " + str(num_disks))

        # Get the UUIDs of the fencing disks specified
        uuid_specified_list = []

        if num_disks == 0:
            self.log("info", "No fencing disks in model.")

        else:

            for fen_disk_url in fen_disk_urls:

                props = self.get_props_from_url(self.ms_node, fen_disk_url)

                self.log("info", "Cluster id: " + cluster_id +
                         ", Properties: " + str(props))

                # Check if all the properties are set
                prop_names = props.keys()

                same_lists = self.compare_disk_props(sorted(prop_names))

                self.assertTrue(same_lists)

                uuid_specified_list.append(props["uuid"])

            uuid_specified_list = uuid_specified_list.sort()

            self.verify_split_brain_protection(vcs_nodes, num_disks,
                                               uuid_specified_list)

    def _check_cluster_properties(self, props):
        """
            Description:
                Verifies that the values of some the properties under the
                cluster are set correctly
        """

        self.log("info", "Checking that the property 'cluster_type' is "
                         "present")
        self.assertTrue("cluster_type" in props)

        self.log("info", "Checking that the property 'cluster_id' is "
                         "present")
        self.assertTrue("cluster_id" in props)

        self.log("info", "Checking that the property 'default_nic_monitor' is "
                         "present")
        self.assertTrue("default_nic_monitor" in props)

        self.log("info", "Checking that the property 'llt_nets' is "
                         "present")
        self.assertTrue("llt_nets" in props)

        self.log("info", "Checking that the property 'low_prio_net' is "
                         "present")
        self.assertTrue("low_prio_net" in props)

    def _verify_cluster_packages_installed(self, node_name, cluster):
        """
            Description:
                Verify packages used under the clustered service are
                installed on the relevant nodes
        """
        if "package" in cluster:

            cluster_packs = cluster["package"]

            for package in cluster_packs:

                props = package

                self.assertTrue("name" in props)

                name = [props["name"]]

                self.check_pkgs_installed(node_name, name)

    def _verify_cluster_vxvm_volume(self, cluster, node_name,
                                    service_group):
        """
            Description:
                Verifies that any vxvm volumes under a clustered service are
                on the right nodes
        """

        # If file-system is in the model under cluster service
        if "file-system" in cluster:

            fss = cluster["file-system"]

            # Get the states of the service groups on the node
            gp_states = self.run_vcs_hagrp_display_command(node_name,
                                                           service_group,
                                                           "State")

            # For each filesystem in the model
            for filesys in fss:

                self.log("info", "VXVM Volume URL: {0}".format(filesys))

                # Get the url of the inherited path in the model
                vxvm = self.deref_inherited_path(self.ms_node, filesys["url"])

                self.log("info", "Inherited from {0}".format(vxvm))

                # Get the URL and the properties of the volume group
                volume_grp_url = "/".join(vxvm.split("/")[:-2])
                vol_grp_props = self.get_props_from_url(self.ms_node,
                                                        volume_grp_url)

                # Get name of volume group from the properties
                volume_grp = vol_grp_props["volume_group_name"]

                # Get the name of the volume from the url
                volume = vxvm.split("/")[-1]

                # Get the url of the vcs clustered service in the model
                url = cluster["vcs-clustered-service"]["url"]

                # Get the name of the service from the url
                service = url.split("/")[-1]

                # If the service name is in the service group name
                if service in service_group:

                    self.log("info", "Service '{0}' is in Service group '{1}'"
                             .format(service,
                                     service_group))

                    for state in gp_states["State"]:

                        # If the service group is online
                        if state["VALUE"] == "|ONLINE|":

                            self.log("info", "Service group '{0}' is ONLINE"
                                     .format(service_group))

                            self.log("info", "Checking if volume '{0}' is on "
                                             "{1}".format(volume,
                                                          state["SYSTEM"]))

                            # This command checks if the vxvm volume is
                            # available on the node
                            cmd = "/sbin/vxprint -g {0} | grep ' {1} '"\
                                .format(volume_grp, volume)

                            stdout, stderr, rc = self.run_command(
                                state["SYSTEM"], cmd, su_root=True)

                            self.assertNotEqual([], stdout)
                            self.assertEqual([], stderr)
                            self.assertEqual(0, rc)

                            self.log("info", "VXVM volume is on {0}".format(
                                state["SYSTEM"]))

    def _verify_haconfig_props(self, cluster, resource, node_name):
        """
            Description:
                Verify ha-service-config item properties
        """
        for config in cluster["ha-service-config"]:

            # Get dictionary of ha-service-config properties
            props = cluster["ha-service-config"]

            self.log("info", "Ha-Service-Config properties : {0}"
                     .format(props))

            for res in resource:
                # Check that this resource is an Application.
                cmd = self.vcs.get_hares_cmd(
                    "-display {0} -type Application".format(res))
                stdout, stderr, rc = self.run_command(node_name, cmd,
                                                      su_root=True)
                if [] != stdout and [] == stderr and rc == 1:
                    self.log("info", "This resource {0} is not of type "
                                     "Application, skipping.".format(res))
                    continue

                self.assertEquals([], stderr)
                self.assertEquals(0, rc)
                self.assertNotEquals([], stdout)

                # if the cluster name is in the resource and it's an
                # Application Resource.
                if cluster["vcs-clustered-service"]["name"] in res:

                    if "service_id" in config:

                        # If the service id is not in the resource continue
                        # onto the next one
                        if config["service_id"] not in res:

                            continue

                    # Display resource information for each resource
                    hares_display = self.run_vcs_hares_display_command(
                        node_name, res)

                    if "dependency_list" in config:

                        depend_list = config["dependency_list"].split(",")

                        for depend in depend_list:
                            self.log("info", "Checking that dependency '{0}' "
                                             "is available in the VCS cluster"
                                     .format(depend))

                            self.assertTrue(depend in item
                                            for item in resource)

                    self.log("info", "Checking that clean timeout is "
                                     "correct")

                    self.assertTrue("CleanTimeout" in hares_display)
                    self.assertEqual(
                        config["clean_timeout"],
                        hares_display["CleanTimeout"][0]["VALUE"])

                    self.log("info", "Checking that fault on monitor "
                                     "timeouts is correct")

                    self.assertTrue("FaultOnMonitorTimeouts" in hares_display)
                    self.assertEqual(
                        config["fault_on_monitor_timeouts"],
                        hares_display["FaultOnMonitor"
                                      "Timeouts"][0]["VALUE"])

                    self.log("info", "Checking that tolerance_limit is "
                                     "correct")

                    self.assertTrue("ToleranceLimit" in hares_display)
                    self.assertEqual(
                        config["tolerance_limit"],
                        hares_display["ToleranceLimit"][0]["VALUE"])

                    if "status_timeout" in config:

                        self.log("info", "Checking correct timeout set")

                        self.assertTrue("MonitorTimeout" in hares_display)
                        self.assertEqual(
                            config["status_timeout"],
                            hares_display["MonitorTimeout"][0]["VALUE"])

                    if "restart_limit" in config:

                        self.log("info", "Checking that restart limit is "
                                         "correct")

                        self.assertTrue("RestartLimit" in hares_display)
                        self.assertEqual(
                            config["restart_limit"],
                            hares_display["RestartLimit"][0]["VALUE"])

                    if "status_interval" in config:

                        self.log("info", "Checking that status interval "
                                         "is correct")

                        self.assertTrue("MonitorInterval" in hares_display)
                        self.assertEqual(
                            config["status_interval"],
                            hares_display["MonitorInterval"][0]["VALUE"])

                    if "startup_retry_limit" in config:

                        self.log("info", "Checking that "
                                         "startup_retry_limit is correct")

                        self.assertTrue("OnlineRetryLimit" in hares_display)
                        self.assertEqual(
                            config["startup_retry_limit"],
                            hares_display["OnlineRetryLimit"][0]["VALUE"])

                    self.log("info", "'ha-service-config check complete")

                    self.log("info", "Checking Online Timeout and Offline "
                                     "Timeout properties from "
                                     "vcs-cluster-service")
                    self.assertEqual(
                        cluster["vcs-clustered-service"]["online_timeout"],
                        hares_display["OnlineTimeout"][0]["VALUE"])

                    self.assertEqual(
                        cluster["vcs-clustered-service"]
                        ["offline_timeout"],
                        hares_display["OfflineTimeout"][0]["VALUE"])

    def _verify_gabconfig(self, vcs_nodes):
        """
            Description:
                Verify gabconfig is set correctly according to the model and
                that the correct nodes are running
        """

        gabconfig = self.vcs.get_gabconfig_cmd()

        gabconfig_cmd = gabconfig + " | grep gen"

        std_out, std_err, r_code = self.run_command(vcs_nodes[0],
                                                    gabconfig_cmd,
                                                    su_root=True)

        self.assertEqual(0, r_code)
        self.assertEqual([], std_err)
        self.assertNotEqual([], std_out)

        for line in std_out:
            new_std_out = line.split()

            self.log("info", "Checking the the number of vcs nodes in "
                             "gabconfig '{0}' is equal to the number of "
                             "vcs nodes in the model '{1}'"
                     .format(len(new_std_out[-1]), len(vcs_nodes)))

            self.assertEqual(len(vcs_nodes), len(new_std_out[-1]))

        hastatus = self.vcs.get_hastatus_sum_cmd()

        hastatus_cmd = hastatus + " | /bin/grep RUNNING"

        std_out, std_err, r_code = self.run_command(vcs_nodes[0],
                                                    hastatus_cmd,
                                                    su_root=True)

        self.assertEqual(0, r_code)
        self.assertEqual([], std_err)
        self.assertNotEqual([], std_out)

        for node in vcs_nodes:
            self.log("info", "Checking that {0} is running".format(node))
            self.assertTrue(node in line for line in std_out)

    def _verify_vcs_network_host(self, interfaces, llt_nets, node,
                                 cluster_name, node_hostname,
                                 hosts_per_network):
        """
            Description:
                Verify vcs-network-host items
        """

        for if_url in interfaces:

            network_name = self.get_props_from_url(self.ms_node,
                                                   if_url,
                                                   'network_name')

            props = self.get_props_from_url(self.ms_node, if_url)

            if network_name in llt_nets:

                macadd = props["macaddress"].upper()

                cmd = "/sbin/lltconfig -a list | /bin/grep {0}".format(macadd)

                stdout, stderr, rc = self.run_command(node, cmd,
                                                      su_root=True)
                self.assertNotEqual([], stdout)
                self.assertEqual(0, rc)
                self.assertEqual([], stderr)
                continue

            # Only network interfaces with associated network name have
            # a NIC Service Group
            if network_name:

                dev_name = self.get_props_from_url(self.ms_node,
                                                   if_url,
                                                   'device_name')
                if "." in dev_name:

                    dev_name = dev_name.replace(".", "_")

                self.log("info", "Node: " + node +
                                 ", network_name: " + network_name +
                                 ", dev_name: " + dev_name)

                sys = node_hostname

                res_name = self.vcs.generate_nic_resource_name(
                    cluster_name, dev_name)

                # Ensure the NIC resource is in ONLINE state
                res_state_per_node = self.get_res_state_per_node(
                    node, res_name)

                self.assertEqual("online", res_state_per_node[sys])

                # Find the NetworkHosts of this node, as they
                # are seen by VCS
                cmd = self.vcs.get_hares_resource_attribute(
                    res_name, "NetworkHosts") + " -sys '{0}'"\
                    .format(sys)

                stdout, stderr, rc = self.run_command(node, cmd,
                                                      su_root=True)
                self.assertEqual(0, rc)
                self.assertEqual([], stderr)

                if stdout == []:

                    cmd = self.vcs.get_hares_resource_attribute(
                        res_name, "NetworkHosts") + " -sys 'global'"

                    stdout, stderr, rc = self.run_command(node, cmd,
                                                          su_root=True)
                    self.assertEqual(0, rc)
                    self.assertEqual([], stderr)

                params = stdout[1].split(None, 3)

                out_hosts = params[3].upper().split() \
                    if len(params) > 3 else "No value"

                self.log("info", ", Node: " + node + ", out_hosts: " +
                         str(out_hosts))

                if network_name in hosts_per_network:

                    # Compare if the network hosts of this node match
                    # the items specified in the model
                    self.assertEqual(
                        sorted(hosts_per_network[network_name]),
                        sorted(out_hosts))

    def _verify_vip_addresses(self, cluster_url, cluster, nodes):
        """
            Description:
                Verify vip items in vcs-clustered-service
        """

        # If VIP in model, begin checks.
        if 'vip' in cluster:

            vips = cluster["vip"]
            networks = []

            # Get list of networks under the cluster in the LITP model
            network_ints = self.find_children_of_collect(self.ms_node, \
                                        cluster_url, "network-interface")
            for network_int in network_ints:
                networks.append(self.get_props_from_url(
                    self.ms_node, network_int, filter_prop="network_name"))

            # Get the output of ifconfig for each node in the group.
            cmd = self.net.get_ifconfig_cmd()
            ifcfgs = []
            for node in nodes:
                out, err, rc = self.run_command(node, cmd)
                self.assertEqual(0, rc)
                self.assertEqual([], err)
                self.assertNotEqual([], out)
                ifcfgs.extend(out)

            for vip in vips:

                # Gets the network name for each VIP
                vip_network = vip['network_name']

                # Finds corresponding network name
                if vip_network in networks:

                    self.log("info", "Vip {0} network found".format(
                        vip["network_name"]))
                    vip_network_set = True
                    break
                else:
                    vip_network_set = False

                self.assertTrue(vip_network_set,
                                str(vip) + " network_name doesn't exists")

                # Check that the vip is online one a node.
                self.assertTrue(
                    any(vip['ipaddress'] in line for line in ifcfgs))

            return True

    def _verify_dependency_list(self, service_props, cluster_id, service_id,
                                node_name):
        """
            Description:
                Verify that the dependency list property has been applied
                correctly
        """

        test_dependencies_list = []

        # Are there dependencies?
        if "dependency_list" in service_props and len(
                service_props["dependency_list"]) != 0:

            add_row = {}
            add_row["cluster_id"] = cluster_id

            add_row["node_name"] = node_name

            add_row["children"] = service_props['dependency_list'].split(",")

            add_row["parent"] = service_id
            test_dependencies_list.append(add_row)

        # After vcs services loop, check all dependencies found
        for dependency in test_dependencies_list:

            self.log("info", "Checking all dependencies found")
            node_name = dependency['node_name']

            # Find parent service group
            parent_sg = self.vcs.generate_clustered_service_name(
                dependency["parent"], dependency["cluster_id"])
            child_sgs = []

            # Find all child service groups
            for child in dependency['children']:
                child_sgs.append(
                    self.vcs.generate_clustered_service_name(
                        child, dependency["cluster_id"]))

            # Retrieve the output for parent sg deps
            gp_deps = self.run_vcs_hagrp_dep_command(node_name, parent_sg)

            # Assert that the prop and output values match
            for gp_dep in gp_deps:
                # Since hagrp -dep finds either parent and child deps
                # of the sg, if it's a child then skip to next row
                if parent_sg == gp_dep["CHILD"]:
                    continue
                self.assertTrue(gp_dep["PARENT"] == parent_sg)
                self.assertTrue(gp_dep["CHILD"] in child_sgs)

    def _verify_lsb_runtimes_running(self, cluster, nodes):
        """
            Description:
                Verify that the lsb-runtimes are running on online nodes.
        """
        if 'lsb-runtime' not in cluster:
            return True

        for runtime in cluster['lsb-runtime']:
            for node in nodes:
                self.log("info", "Checking is service '{0}' running on node: "
                                 "'{1}'".format(runtime['service_name'], node))
                cmd = self.rhc.get_service_running_cmd(runtime['service_name'])
                out, err, rc = self.run_command(node, cmd, su_root=True)
                self.assertEqual(0, rc)
                self.assertEqual([], err)
                self.assertNotEqual([], out)

    def _verify_services_running(self, cluster, nodes):
        """
            Description:
                Verify that the services are running on online nodes.
        """
        if 'service' not in cluster:
            return True

        for service in cluster['service']:
            for node in nodes:
                self.log("info", "Checking is service '{0}' running on node: "
                                 "'{1}'".format(service['service_name'], node))
                cmd = self.rhc.get_service_running_cmd(service['service_name'])
                out, err, rc = self.run_command(node, cmd, su_root=True)
                self.assertEqual(0, rc)
                self.assertEqual([], err)
                self.assertNotEqual([], out)

    def _verify_default_nic_monitor(self, interfaces, llt_nets, node,
                               cluster_name, node_hostname, hosts_per_network,
                               cluster_props):
        """
            Description:
                Verify vcs-cluster items default_nic_monitor property.
                Story TORF-107259.
        """
        iterf = dict()
        for if_url in interfaces:
            props = self.get_props_from_url(self.ms_node, if_url)
            device_name = props["device_name"]
            if "network_name" in props:
                iterf[device_name] = props["network_name"]

        self.log("info", "default_nic_monitor set to {0}!"\
                    .format(cluster_props["default_nic_monitor"]))
        for dev in iterf:
            if iterf[dev] in llt_nets:
                self.log("info", "Skipping llt net {0}".format(dev))
                continue

            res_name = self.vcs.generate_nic_resource_name(
                                    cluster_name, dev)

            cmd = self.vcs.get_hares_resource_attribute(res_name, \
                                "Mii") + " -sys '{0}'".format(node_hostname)

            stdout, _, _ = self.run_command(node, cmd,
                                      default_asserts=True, su_root=True)

            result = stdout[1].split(' ')[-1]
            self.log("info", "Nic Mii Value {0}".format(result))

            if "netstat" == cluster_props["default_nic_monitor"]:
                # Mii value should always be 0 if netstat used.
                expected = '0'
                self.assertEqual(expected, result)
            else:
                # Mii value should be 0 if NetworkHosts.
                # Mii value should be 1 if no NetworkHosts.
                network = iterf[dev]
                if network in hosts_per_network:
                    self.log("info", "VCS NetworkHosts on Nic")
                    expected = '0'
                    self.assertEqual(expected, result)
                else:
                    self.log("info", "No VCS NetworkHosts on Nic")
                    expected = '1'
                    self.assertEqual(expected, result)

    @attr('all', 'revert', 'system_check', 'vcs', 'vcs_tc01')
    def test_01_p_verify_vcs(self):
        """
        Description:
            Test the 'vcs-cluster', 'vcs-network-host' & 'disk' LITP
            item types.

        Actions:
            1. Get all vcs-clusters under the deployment from the model
            2. For each vcs cluster in model:
                a. Get the properties of the cluster from the model
                b. Verify that cluster properties are set correct in the model
                c. Get urls of all nodes in the vcs-cluster
                d. Create list of nodes under the VCS cluster
                e. Verify all VCS related files exist on all nodes in cluster
                f. Verify the llt, gab, vcs services are running
                g. Verify cluster_id by reading /etc/llttab file
                h. Verify cluster name
                i. Validate MAIN CF
                j .Verify VCS NetworkHost parameters match 'vcs-network-host'
                    in the LITP Model
                k. Verify VCS network hosts
        """
        # 1. Get all vcs-clusters under the deployment from the model
        vcs_cluster_urls = self.find(self.ms_node, "/deployments",
                                     "vcs-cluster", assert_not_empty=False)

        # 2. For each vcs cluster in model:
        for vcs_cluster_url in vcs_cluster_urls:

            # a. Get the properties of the cluster from the model
            cluster_props = \
                self.get_props_from_url(self.ms_node, vcs_cluster_url)

            cluster_id = cluster_props["cluster_id"]
            self.log("info", "Cluster id: " + cluster_id + ", Properties: " +
                     str(cluster_props))

            # b. Verify that cluster properties are set correct in the model
            self._check_cluster_properties(cluster_props)

            cluster_type = cluster_props["cluster_type"]

            # c. Get urls of all nodes in the vcs-cluster
            vcs_nodes_urls = self.find(self.ms_node, vcs_cluster_url, "node")

            vcs_nodes = []

            # d. Create list of nodes under the VCS cluster
            for node in vcs_nodes_urls:

                filename = self.get_node_filename_from_url(self.ms_node, node)

                vcs_nodes.append(filename)

            if vcs_nodes == []:
                self.log("info", "No VCS nodes found")

            # e. Verify all VCS related files exist on all nodes in cluster
            for node in vcs_nodes:

                for conf_f in self.files_paths:

                    self.log("info", node + " Verifying " + conf_f +
                             " on node")

                    self.assertTrue(self.remote_path_exists(node,
                                                            conf_f),
                                    "File {0} not on node {1}"
                                    .format(conf_f, node))

                # f. Verify the llt, gab, vcs services are running
                cmds = []

                for serv in ["llt", "gab", "vcs"]:

                    cmds.append(self.rhc.get_service_running_cmd(serv))

                    for cmd in cmds:

                        self.log("info", node + " Verifying " + cmd)
                        _, std_err, r_code = self.run_command(node,
                                                              cmd,
                                                              su_root=True)
                        self.assertEqual(0, r_code)
                        self.assertEqual([], std_err)

            # g. Verify cluster_id by reading /etc/llttab file.
            grep_cmd = self.rhc.get_grep_file_cmd("/etc/llttab",
                                                  cluster_props["cluster_id"])

            for node in vcs_nodes:

                self.log("info", node + " Verifying cluster_id in {0}"
                         .format("/etc/llttab"))

                _, std_err, r_code = self.run_command(node,
                                                      grep_cmd, su_root=False)

                self.assertEqual(r_code, 0, "non-zero return code")
                self.assertEqual(std_err, [], std_err)

            # h. Verify cluster name.
            cluster_name = vcs_cluster_url.split('/')[-1]

            haclus_cmd = self.vcs.get_haclus_cmd("-value ClusterName")

            for node in vcs_nodes:

                self.log("info", node + " Verify ClusterName {0}"
                         .format(cluster_name))

                std_out, std_err, r_code = self.run_command(node, haclus_cmd,
                                                            su_root=True)

                self.assertEqual(std_out, [cluster_name])
                self.assertEqual(0, r_code)
                self.assertEqual([], std_err)

            # i. Validate MAIN CF
            cmd = self.vcs.validate_main_cf_cmd()

            self.log("info", vcs_nodes[0] + " validate_main_cf_cmd()")

            std_out, std_err, r_code = self.run_command(vcs_nodes[0], cmd,
                                                        su_root=True)

            self.assertEqual(0, r_code)
            self.assertEqual([], std_err)
            self.assertEqual([], std_out)

            self._verify_fencing_disks(vcs_cluster_url, cluster_id,
                                       cluster_type, vcs_nodes)

            # j .Verify VCS NetworkHost parameters match 'vcs-network-host' in
            # the LITP Model
            llt_nets = str(self.get_props_from_url(self.ms_node,
                                                   vcs_cluster_url,
                                                   'llt_nets')).split(",")

            self.log("info", "Cluster id: " + cluster_id + ", llt_nets: " +
                     str(llt_nets))

            # Find network hosts for each of the networks
            hosts_per_network = {}

            network_host_urls = self.find(self.ms_node, vcs_cluster_url,
                                          "vcs-network-host",
                                          assert_not_empty=False)

            # k. Verify VCS network hosts
            for host_url in network_host_urls:

                nh_props = self.get_props_from_url(self.ms_node, host_url)

                net_name = nh_props['network_name']

                ip_addr = str(nh_props['ip'])

                if net_name not in hosts_per_network:
                    hosts_per_network[net_name] = []

                hosts_per_network[net_name].append(ip_addr.upper())

            for node_url in vcs_nodes_urls:

                node = self.get_node_filename_from_url(self.ms_node, node_url)

                node_hostname = self.get_props_from_url(self.ms_node, node_url,
                                                        'hostname')

                interfaces = self.find_children_of_collect(self.ms_node,
                                                           node_url,
                                                           'network-interface')

                self._verify_vcs_network_host(interfaces, llt_nets, node,
                                              cluster_name, node_hostname,
                                              hosts_per_network)

                self._verify_gabconfig(vcs_nodes)

                self._verify_default_nic_monitor(interfaces, llt_nets, node,
                                              cluster_name, node_hostname,
                                             hosts_per_network, cluster_props)

    @attr('all', 'revert', 'system_check', 'vcs', 'vcs_tc02')
    def test_02_verify_sg_vcs_clustered_service(self):
        """
        Description:
            Test the 'vcs-clustered-service' and 'ha-config' items in the
            LITP model

        Actions:
            1. Get all VCS clustered service information from the LITP model
                and put it into a dictionary
            2. Get the url of the cluster that the clustered service is under
            3. Take cluster name from vcs-cluster path
            4. Retrieve service properties to check them
            5. Generate sg name with vcs_utils method
            6. Find all clust.service State value for all the cluster nodes
            7. Check that active/standby item values match with service group
                output result
            8. Check that node_list values match service group output result
            9. Create a list from node_list property
            10. Create a list from service group output node list
            11. Find node name from each property node_list element and
                compare it with the output node name
            12. Verify that packages under the node are installed
            13. Find service resource State values for all the cluster nodes
            14. Verify haconfig item
            15. Verify any VXVM volumes under the clustered service
            16. Verify vip items
            17. Check that services are running on online nodes
            18. Check that lsb-runtimes are running on online nodes
            19. Checks for dependency list
        """

        # 1. Get all VCS clustered service information from the LITP model and
        # put it into a dictionary
        info = self.get_vcs_model_info()

        for cluster in info:

            # Splits up the URL of the clustered service
            url_parts = cluster["vcs-clustered-service"]["url"].split("/")

            # 2. Get the url of the cluster that the clustered service is under
            vcs_cluster_url = "/".join(url_parts[:-2])

            self.log("info", "Cluster URL : {0}".format(vcs_cluster_url))

            # 3. Take cluster name from vcs-cluster path
            cluster_id = url_parts[-3]
            vcs_nodes = self.find(self.ms_node, vcs_cluster_url, "node")

            # Take first cluster node name to use it for ha methods
            node_name = self.get_props_from_url(self.ms_node, vcs_nodes[0],
                                                'hostname')

            # 4. Retrieve service properties to check them
            service_props = cluster["vcs-clustered-service"]

            # Take service id from its path
            service_id = url_parts[-1]

            # 5. Generate sg name with vcs_utils method
            service_group = self.vcs.generate_clustered_service_name(
                service_id, cluster_id)

            self.log("info", "Checking {0} Service Group State".format(
                service_id))

            # 6. Find all clust.service State value for all the cluster nodes
            gp_states = self.run_vcs_hagrp_display_command(node_name,
                                                           service_group,
                                                           "State")
            # 7. Check that active/standby item values match with
            # service group output result
            actives = standbys = 0

            for node_state in gp_states['State']:
                if "ONLINE" in node_state['VALUE']:
                    actives += 1
                else:
                    standbys += 1

            self.assertTrue(actives == int(service_props['active']))
            self.assertTrue(standbys == int(service_props['standby']))

            # 8. Check that node_list values match service group output result
            self.log("info", "Checking {0} Service Group Node list"
                     .format(service_id))

            gp_node_list = self.run_vcs_hagrp_display_command(
                node_name, service_group, "AutoStartList")

            # 9. Create a list from node_list property
            node_list = service_props['node_list'].split(",")

            # 10. Create a list from service group output node list
            for gp_node_row in gp_node_list['AutoStartList']:

                gp_nodes = gp_node_row['VALUE'].split()

                # The lists must have equal length
                self.assertTrue(len(node_list) == len(gp_nodes))

                node_hostnames = []
                # 11. Find node name from each property node_list element
                # and compare it with the output node name
                for i in range(len(node_list)):

                    # Get hostname of nodes in node list
                    node_list_name = self.get_props_from_url(self.ms_node,
                                                             vcs_cluster_url +
                                                             "/nodes/" +
                                                             node_list[i],
                                                             'hostname')

                    # If there are 0 standby nodes disregard order of
                    # AutoStartList
                    if service_props['standby'] == "0":
                        self.assertTrue(node_list_name in gp_nodes)

                    # If there is a standby node check that the AutoStartList
                    # is in the correct order
                    else:
                        self.assertTrue(node_list_name == gp_nodes[i])
                    node_hostnames.append(node_list_name)

                    # 12. Verify that packages under the node are installed
                    self._verify_cluster_packages_installed(node_list_name,
                                                            cluster)

            # 13. Find service resource State values for all the cluster nodes
            self.log("info", "Checking {0} Resource State"
                     .format(service_id))

            resource = self.run_vcs_hagrp_resource_command(node_name,
                                                           service_group)

            # Gets the states of the resource
            res_states = self.run_vcs_hares_display_command(node_name,
                                                            resource[0],
                                                            "State")
            # 14. Verify haconfig item
            # ha-service-config item is optional and is not supported in
            # combination with deprecated 'lsb-runtime' item type
            if "ha-service-config" in cluster:
                self._verify_haconfig_props(cluster, resource, node_name)

            # 15. Verify any VXVM volumes under the clustered service
            self._verify_cluster_vxvm_volume(cluster, node_name,
                                             service_group)
            # 16. Verify vip items
            self._verify_vip_addresses(vcs_cluster_url, cluster,
                                       node_hostnames)

            # Check that active/standby item values match with
            # resource output result
            actives = standbys = 0
            online_nodes = []
            for node_state in res_states['State']:
                if "ONLINE" in node_state['VALUE']:
                    actives += 1
                    online_nodes.append(node_state['SYSTEM'])
                else:
                    standbys += 1

            self.assertTrue(actives == int(service_props['active']),
                            str(actives) + "!=" + service_props['active'])

            self.assertTrue(standbys == int(service_props['standby']))

            # 17. Check that services are running on online nodes
            self._verify_services_running(cluster, online_nodes)

            # 18. Check that lsb-runtimes are running on online nodes
            self._verify_lsb_runtimes_running(cluster, online_nodes)

            # 19. Checks for dependency list
            self._verify_dependency_list(service_props, cluster_id, service_id,
                                         node_name)
