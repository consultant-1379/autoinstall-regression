"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2015
@author:    Marco Gibboni / Bryan O'Neill
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from networking_utils import NetworkingUtils
from vcs_utils import VCSUtils
from storage_utils import StorageUtils
import test_constants
import simplejson
import re


def populate_ip_map(ip_map, node_hst, ipversion, ip_addr_ver):
    """
    Populate ipv4/ipv6 version
    """
    if len(node_hst) == len(ipversion):
        for tlen in range(len(node_hst)):
            ip_map[node_hst[tlen]] = {ip_addr_ver: ipversion[tlen]}
    if len(ipversion) == 1:
        for tlen in range(len(node_hst)):
            ip_map[node_hst[tlen]] = {ip_addr_ver: ipversion[0]}
    return ip_map


def get_ip_map(vm_net, node_hst):
    """
    Populate IP MAP dictionary
    """

    ip_map = {}
    ipaddr = []
    if 'ipaddresses' in vm_net:
        if vm_net['ipaddresses'] != "dhcp":
            # CHECK NODE LIST MATCHES NUMBER OF IP ADDRESSES
            ipaddr = vm_net['ipaddresses'].split(",")
    ipv6addr = []
    if 'ipv6addresses' in vm_net:
        # CHECK NODE LIST MATCHES NUMBER OF IPV6 ADDRESSES
        ipv6addr = vm_net['ipv6addresses'].split(",")
    # POPULATE A NODE IP MAPPING IF PRESENT
    if ipaddr != [] and ipv6addr != []:
        if len(node_hst) == len(ipaddr) and \
                len(node_hst) == len(ipv6addr):
            for tlen in range(len(node_hst)):
                ip_map[node_hst[tlen]] = \
                    {"ipv4": ipaddr[tlen], "ipv6": ipv6addr[tlen]}
        if len(ipaddr) == 1 and len(ipv6addr) == 1:
            for tlen in range(len(node_hst)):
                ip_map[node_hst[tlen]] = \
                        {"ipv4": ipaddr[0], "ipv6": ipv6addr[0]}
    if ipaddr == [] and ipv6addr != []:
        ip_map = populate_ip_map(ip_map, node_hst, ipv6addr, "ipv6")
    if ipaddr != [] and ipv6addr == []:
        ip_map = populate_ip_map(ip_map, node_hst, ipaddr, "ipv4")
    return ip_map


class VCSVM(GenericTest):
    """
    This test has been created merging VCS functionality regression test
        with VCS KGB stories.
    The KGB stories included are:
        11943: checking "chkconfig" for tuned package in vm-service function.
        7516: IPv6/GW addresses check added to vm-network-interface function.
        7185: Default routes check added to vm-network-interface function.
        9492: Testing VM hostnames (new own function added).
        7815: Testing 'vm-nfs-mount' items (new own function added).
        8994: VM timezones check (new own function added).
        8188: VM DHCP check (if present; new own function added).
        7848: MAC address uniqueness check added in vm-network-interface
                                                                    function.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(VCSVM, self).setUp()
        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.clusters = self.model['clusters']
        self.rhc = RHCmdUtils()
        self.vcs = VCSUtils()
        self.net = NetworkingUtils()
        self.stor = StorageUtils()
        self.dhcp_ranges = None

    def tearDown(self):
        """ Teardown run after every test """

        super(VCSVM, self).tearDown()

    def get_vcs_vm_model_info(self):
        """
        Get all information relating to VMs from the litp model.
        This information returned is a list of Service Groups. Each Service
        group is a dict. including details for the following types under the
        Service Group:
            * vm-image
            * vm-service
            * vcs-clustered-service
            * vm-package
            * vm-alias
            * vm-nfs-mount
            * vm-network-interface
            * vm-yum-repo
            * vm-ssh-key
        """
        service_groups = []
        type_list = ['vm-alias', 'vm-yum-repo', 'vm-package', 'vm-nfs-mount',
                     'vm-network-interface', 'vm-ssh-key', 'vm-service']
        prop_dict = {}
        service_group = {}
        infra_dict = {}

        urls = self.find(self.ms_node, '/software', 'vm-image',
                         assert_not_empty=False)
        for url in urls:
            props = self.get_props_from_url(self.ms_node, url)
            prop_dict['url'] = url
            for prop in props:
                prop_dict[prop] = props[prop]
            infra_dict[props['name']] = prop_dict
        prop_dict = {}

        for cluster in self.model['clusters']:
            clus_servs = self.find(self.ms_node, cluster['url'],
                                   'vcs-clustered-service',
                                   assert_not_empty=False)
            for serv in clus_servs:
                # Check if this clustered service is a vm service
                check = self.find(self.ms_node, serv, 'vm-service',
                                  assert_not_empty=False)
                if not check:
                    continue

                # This clustered service is a vm-service.
                props = self.get_props_from_url(self.ms_node, serv)
                for prop in props:
                    prop_dict[prop] = props[prop]
                prop_dict['url'] = serv
                service_group['vcs-clustered-service'] = prop_dict
                prop_dict = {}

                for itype in type_list:
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
                            if itype == 'vm-service':
                                service_group[itype] = prop_dict
                            else:
                                service_group[itype] = []
                                service_group[itype].append(prop_dict)
                        prop_dict = {}

                vm_image_name = service_group['vm-service']['image_name']
                service_group['vm-image'] = infra_dict[vm_image_name]

                nodes = self._get_vm_node_names(
                    service_group
                    ['vcs-clustered-service']['node_list'].split(','),
                    cluster)
                service_group['nodes'] = nodes
                service_group['cluster'] = cluster
                service_group['cluster']['id'] = cluster['url'].split('/')[-1]
                service_groups.append(service_group)
                service_group = {}

        self.log("info", "Printing dict from get_vcs_vm_model_info()")
        self._print_list(0, service_groups)
        self.log("info", "Finished printing dict")
        return service_groups

    @staticmethod
    def _get_vm_node_names(vm_nodes, cluster):
        """
        Get the path ids and hostnames of vms.
        """
        nodes = {}
        for vm_n in vm_nodes:
            path = cluster['url'] + '/nodes/' + vm_n
            for node in cluster['nodes']:
                if path in node.values():
                    nodes[vm_n] = node['name']
        return nodes

    @staticmethod
    def _format_ipv6_to_list(ipv6_addr):
        """
        This function takes an IPv6 address as a string and returns a list
        containing 8 elements. Each element is a decimal number respective to
        each hexadecimal segment of the address.
        If a network prefix is included in the address this will be appended
        to the list as the 9th element.
        eg:
        2001:db8:85a3::7516:10 ---> [8193, 3512, 34211, 0, 0, 0, 29974, 16]

        2001:db8:85a3::7516:10/64 --->
                                    [8193, 3512, 34211, 0, 0, 0, 29974, 16, 64]
        """
        ret_ip = [0 * n for n in xrange(8)]
        # Remove network prefix if present
        ipv6_addr = ipv6_addr.split('/')
        if len(ipv6_addr) == 2:
            prefix = ipv6_addr[1]
            ipv6_addr = ipv6_addr[0]
        else:
            prefix = False
            ipv6_addr = ipv6_addr[0]

        splitip = ipv6_addr.split('::')
        if len(splitip) == 2:
            lhs = splitip[0].split(':')
            rhs = splitip[1].split(':')

            for var in xrange(len(lhs)):
                ret_ip[var] = int(lhs[var], 16)

            for var in xrange(len(rhs)):
                ret_ip[7 - var] = int(rhs[(len(rhs) - 1) - var], 16)
        else:
            ipv6_addr = ipv6_addr.split(':')
            for var in xrange(len(ipv6_addr)):
                ret_ip[var] = int(ipv6_addr[var], 16)

        print "prefix: ", prefix
        print ret_ip
        if prefix:
            ret_ip.append(int(prefix, 10))
            print "10: ", int(prefix, 10)
        else:
            ret_ip.append(64)
        print ret_ip
        return ret_ip

    def _check_vcs_clustered_service(self, sv_gp, lp_cs_nm, lp_nd, lp_cs,
                                     v_cs_nm, hares, hagrp, hastat):
        """
        Check the 'vcs-clustered-service' type for a service group.
        """
        self.log('info', 'Check Service Group: "{0}" is listed for all '
                 'nodes in node_list, on node: "{1}"'.format(lp_cs_nm, lp_nd))
        nodes_listed = []
        for svg in hastat['SERVICE_GROUPS']:
            if svg['GROUP'] == v_cs_nm:
                nodes_listed.append(svg['SYSTEM'])
        for node in sv_gp['nodes']:
            self.assertTrue(sv_gp['nodes'][node] in nodes_listed)

        # Check online timeout
        self.log('info', 'Check online_timeout for Service Group: "{0}" on'
                 ' node: "{1}"'.format(lp_cs_nm, lp_nd))
        self.assertTrue(hares['OnlineTimeout'][0]['VALUE'] ==
                        lp_cs['online_timeout'])

        # Check offline timeout
        self.log('info', 'Check offline_timeout for Service Group: "{0}" '
                 'on node: "{1}"'.format(lp_cs_nm, lp_nd))
        self.assertTrue(hares['OfflineTimeout'][0]['VALUE'] ==
                        lp_cs['offline_timeout'])

        # Check active standby
        self.log('info',
                 'Check active/standby for Service Group: "{0}" on '
                 'node: "{1}"'.format(lp_cs_nm, lp_nd))
        active = standby = 0
        sv_gp['node-state'] = {}
        for state in hagrp['State']:
            if state['VALUE'] == '|ONLINE|':
                active += 1
                sv_gp['node-state'][state['SYSTEM']] = True
            else:
                standby += 1
                sv_gp['node-state'][state['SYSTEM']] = False
        self.assertEqual(lp_cs['active'], str(active))
        self.assertEqual(lp_cs['standby'], str(standby))

    def _check_vm_service(self, sv_gp, hares,
                          vm_nodes):
        """
        Check the 'vm-service' type for a service group.
        """
        # Check cleanup command
        self.log('info',
            'Check cleanup_command for Service: "{0}"'.\
                format(sv_gp['vm-service']['service_name']))
        self.assertEqual(hares['CleanProgram'][0]['VALUE'],
                         sv_gp['vm-service']['cleanup_command'])

        for node in sv_gp['nodes']:

            if not sv_gp['node-state'][sv_gp['nodes'][node]]:
                # CHECK Service is not running and continue the next
                # node in the loop
                if "status_command" in sv_gp['vm-service']:
                    _, _, rc = self.run_command(sv_gp['nodes'][node],
                        sv_gp['vm-service']['status_command'], su_root=True)
                    self.assertNotEqual(0, rc)
                else:
                    _, _, rc = self.get_service_status(sv_gp['nodes'][node],
                                sv_gp['vm-service']['service_name'],
                                assert_running=False)
                    self.assertNotEqual(0, rc)
                continue

            # Check Service is running
            if "status_command" in sv_gp['vm-service']:
                _, _, rc = self.run_command(sv_gp['nodes'][node],
                    sv_gp['vm-service']['status_command'], su_root=True)
                self.assertEqual(0, rc)
            else:
                self.get_service_status(sv_gp['nodes'][node],
                        sv_gp['vm-service']['service_name'])

            # Get dominfo for service, from this check cpus, memory
            cmd = '/usr/bin/virsh dominfo {0}'.\
                    format(sv_gp['vm-service']['service_name'])
            out, err, rc = self.run_command(sv_gp['nodes'][node],
                                cmd, su_root=True)
            self.assertEqual(0, rc)
            self.assertEqual([], err)
            self.assertNotEqual([], out)
            dominfo = {}
            for line in out:
                line = line.split(':')
                dominfo[line[0]] = line[1].strip(' ')

            # Check adaptor version
            self.log('info',
                     'Check adaptor version for Service Group: "{0}" on '
                     'node: "{1}"'.\
                     format(sv_gp['vcs-clustered-service']['name'],
                     sv_gp['nodes'][node]))
            cmd = self.rhc.check_pkg_installed(
                ['ERIClitpmnlibvirt_CXP9031529-{0}'
                 .format(sv_gp['vm-service']['adaptor_version'])])
            out, err, rc = self.run_command(sv_gp['nodes'][node], cmd)
            self.assertEqual(0, rc)
            self.assertEqual([], err)
            self.assertNotEqual([], out)

            # Check cpus
            self.log('info',
                'Check number of cpus for Service: "{0}" on '
                'node: "{1}"'.format(sv_gp['vcs-clustered-service']['name'],
                 sv_gp['nodes'][node]))
            self.assertEqual(sv_gp['vm-service']['cpus'], dominfo['CPU(s)'])

            # Check memory
            self.log('info',
                'Check memory for Service: "{0}" on '
                'node: "{1}"'.format(sv_gp['vcs-clustered-service']['name'],
                       sv_gp['nodes'][node]))
            dominfo['Max memory'] = dominfo['Max memory'].split(' ')[0]
            sv_gp['vm-service']['ram'] = sv_gp['vm-service']['ram'].strip('M')
            v_ram = str(int(dominfo['Max memory']) / 1024)
            self.assertEqual(sv_gp['vm-service']['ram'], v_ram)

            # Check the internal-status-check.
            self.log('info',
                     'Check internal_status_check for Service: "{0}" on '
                     'VM node: "{1}", on Peer node: "{2}"'
                     .format(sv_gp['vm-service']['service_name'],
                             vm_nodes[node],
                             sv_gp['nodes'][node]))

            cmd = self.rhc.get_cat_cmd('{0}/{1}/config.json'.format(
                test_constants.LIBVIRT_INSTANCES_DIR,
                sv_gp['vm-service']['service_name']))
            out, err, rc = self.run_command(sv_gp['nodes'][node], cmd)
            self.assertEqual([], err)
            self.assertNotEqual([], out)
            self.assertEqual(0, rc)
            conf = simplejson.loads(out[0])
            status = \
                conf['adaptor_data']['internal_status_check']['active']
            if sv_gp['vm-service']['internal_status_check'] == 'on':
                self.assertEqual('on', status)
            else:
                self.assertEqual('off', status)

            # Check if vmmonitord is running.
            self.log('info',
                     'Check "vmmonitord" is running for Service: "{0}" on '
                     'VM node: "{1}", on Peer node: "{2}"'
                     .format(sv_gp['vm-service']['service_name'],
                             vm_nodes[node],
                             sv_gp['nodes'][node]))
            cmd = self.rhc.get_service_running_cmd('vmmonitord')
            out, err, rc = self.run_command_via_node(sv_gp['nodes'][node],
                                                     vm_nodes[node], cmd)
            self.assertEqual([], err)
            self.assertNotEqual([], out)
            self.assertEqual(0, rc)

            # Check if tuned is installed on host node
            self.log('info',
                     'Check "tuned" is installed for Service: "{0}" on '
                     'Peer node: "{1}"'
                     .format(sv_gp['vm-service']['service_name'],
                     sv_gp['nodes'][node]))
            cmd = self.rhc.check_pkg_installed(['tuned'])
            out, err, rc = self.run_command(sv_gp['nodes'][node], cmd)
            self.assertEqual([], err)
            self.assertNotEqual([], out)
            self.assertEqual(0, rc)

            # Check if tuned is running
            self.log('info',
                     'Check "tuned" is running for Service: "{0}" on '
                     ' on Peer node: "{1}"'
                     .format(sv_gp['vm-service']['service_name'],
                             sv_gp['nodes'][node]))
            cmd = self.rhc.get_service_running_cmd('tuned')
            out, err, rc = self.run_command(sv_gp['nodes'][node], cmd)
            self.assertEqual([], err)
            self.assertNotEqual([], out)
            self.assertEqual(0, rc)

            # Check if tuned package is active
            self.log('info',
                     'Check "tuned" package is active for Service: "{0}"'
                     ' on VM node: "{1}", on Peer node: "{2}"'
                     .format(sv_gp['vm-service']['service_name'],
                             vm_nodes[node],
                             sv_gp['nodes'][node]))
            cmd = "/sbin/chkconfig --list tuned"
            out, err, rc = self.run_command(sv_gp['nodes'][node], cmd)
            active_out = 'tuned         0:off\t1:off\t2:off' \
                         '\t3:on\t4:on\t5:on\t6:off'
            self.assertEqual([], err)
            self.assertEqual([active_out], out)
            self.assertEqual(0, rc)

    def _check_vm_network_interface(self, sv_gp, lp_cs, vm_nodes):
        """
        Check the 'vm-network-interface' type for a service group.
        """
        for node in sv_gp['nodes']:
            if not sv_gp['node-state'][sv_gp['nodes'][node]]:
                continue

            node_rh_ver = self.get_rhelver_used_on_node(vm_nodes[node],
                                                        sv_gp['nodes'][node])

            cmd = self.net.get_ifconfig_cmd()
            out, err, rc = self.run_command_via_node(sv_gp['nodes'][node],
                                                     vm_nodes[node], cmd)
            self.assertEqual(0, rc)
            self.assertEqual([], err)
            self.assertNotEqual([], out)
            ifconfig = out
            macs = []

            # CREATE VM NETWORK MAPPING (NOT USING THE LITP EXPOSED PROPERTY)
            node_hst = sv_gp['vcs-clustered-service']['node_list'].split(",")
            act_hst = sv_gp['vcs-clustered-service']['active']
            stb_hst = sv_gp['vcs-clustered-service']['standby']
            total_hst = int(act_hst) + int(stb_hst)
            self.assertEqual(len(node_hst), total_hst)
            for vm_net in sv_gp['vm-network-interface']:
                ip_map = {}
                ip_map = get_ip_map(vm_net, node_hst)

                # Chech eth is up
                cmd = "/sbin/ifconfig | grep -E '^{0} |^{0}:'"\
                      .format(vm_net["device_name"])
                out, err, rc = self.run_command_via_node(
                    sv_gp['nodes'][node],
                    vm_nodes[node],
                    cmd)

                self.log('info',
                         'Checking eth: "{0}" UP for Service Group: '
                         '"{1}" on VM node: "{2}", on Peer node: "{3}"'
                         .format(vm_net["device_name"],
                                 lp_cs['name'],
                                 vm_nodes[node],
                                 sv_gp['nodes'][node]
                                 )
                         )
                self.assertEqual(0, rc)
                self.assertEqual([], err)
                self.assertNotEqual([], out)
                # Check mac address uniqueness
                self.assertTrue(out[0] not in macs)
                macs.append(out[0])

                ifcfg_dict = self.net.get_ifcfg_dict(ifconfig,
                                                     vm_net["device_name"],
                                                     os_ver=node_rh_ver)

                default_gw_cmd = self.net.get_route_gw_ips_cmd()

                # Check correct mac prefix if supplied.
                if 'mac_prefix' in vm_net:
                    self.assertTrue(
                        ifcfg_dict["MAC"].lower().startswith(
                            vm_net['mac_prefix'].lower())
                    )

                if 'ipaddresses' in vm_net:
                    if vm_net['ipaddresses'] == 'dhcp':
                        self._check_vm_dhcp(vm_nodes[node],
                                  sv_gp['nodes'][node],
                                  lp_cs['name'], vm_net['device_name'])
                        continue

                if 'ipv4' in ip_map[node]:
                    self.log('info', 'Checking ip address "{0}" on eth: '
                             '"{1}" for Service Group: "{2}" on VM node: '
                             '"{3}", on Peer node: "{4}"'
                             .format(ip_map[node]['ipv4'],
                                     vm_net["device_name"],
                                     lp_cs['name'],
                                     vm_nodes[node],
                                     sv_gp['nodes'][node]
                                     )
                             )
                    self.assertEqual(ip_map[node]['ipv4'],
                                     self.net.get_ipv4_from_dict(ifcfg_dict))
                    # PING IP AND MAKE SURE REACHABLE
                    self.assertTrue(self.is_ip_pingable(sv_gp['nodes'][node],
                        ip_map[node]['ipv4']))
                if 'ipv6' in ip_map[node]:
                    if '/' not in ip_map[node]['ipv6']:
                        ip_map[node]['ipv6'] += '/64'
                    self.log('info', 'Checking ipv6 address "{0}" on eth: '
                             '"{1}" for Service Group: "{2}" on VM node: '
                             '"{3}", on Peer node: "{4}"'
                             .format(ip_map[node]['ipv6'],
                                     vm_net["device_name"],
                                     lp_cs['name'],
                                     vm_nodes[node],
                                     sv_gp['nodes'][node]
                                     )
                             )
                    cmd = "/sbin/ip -6 addr show {0} |"\
                                " awk 'NR == 2 {{print}}'"\
                                .format(vm_net["device_name"])
                    out, err, rc = self.run_command_via_node(
                        sv_gp['nodes'][node],
                        vm_nodes[node],
                        cmd)
                    self.assertEqual(['inet6 {0} scope global'.
                                        format(ip_map[node]['ipv6'])], out)
                    ip6_addrs = self.net.get_ipv6_from_dict(ifcfg_dict)
                    ipv6 = self._format_ipv6_to_list(ip_map[node]['ipv6'])
                    self.assertTrue(
                        any(ipv6 == self._format_ipv6_to_list(ip)
                            for ip in ip6_addrs))
                    # metadata check here:
                    cmd = "/bin/cat {0}/ifcfg-{1}"\
                      " | /bin/grep IPV6ADDR=".\
                        format(test_constants.NETWORK_SCRIPTS_DIR,
                        vm_net["device_name"])
                    out, err, rc = \
                        self.run_command_via_node(sv_gp['nodes'][node],
                            vm_nodes[node], cmd)
                    self.assertEqual(0, rc)
                    self.assertEqual([], err)
                    self.assertNotEqual([], out)
                    self.assertTrue(ip_map[node]['ipv6'].split("/")[0] in \
                                out[0].split("=")[-1])

                if 'gateway' in vm_net:
                    self.log('info',
                             'Checking eth: "{0}" gateway for Service '
                             'Group: "{1}" on VM node: "{2}", on Peer '
                             'node: "{3}"'
                             .format(vm_net["device_name"],
                                     lp_cs['name'],
                                     vm_nodes[node],
                                     sv_gp['nodes'][node]
                                     )
                             )
                    file_path = "{0}/ifcfg-{1}".format(
                        test_constants.NETWORK_SCRIPTS_DIR,
                        vm_net["device_name"])
                    cmd = '/bin/cat {0} | grep GATEWAY={1}'.format(
                        file_path, vm_net['gateway'])
                    out, err, rc = self.run_command_via_node(
                        sv_gp['nodes'][node],
                        vm_nodes[node],
                        cmd)
                    self.assertEqual(0, rc)
                    self.assertEqual([], err)
                    self.assertNotEqual([], out)
                    # Default route address check
                    out, err, rc = self.run_command_via_node(
                        sv_gp['nodes'][node],
                        vm_nodes[node],
                        default_gw_cmd)
                    self.assertTrue(vm_net['gateway'] in out[0])

                if 'gateway6' in vm_net:
                    self.log('info',
                             'Checking eth: "{0}" gateway6 for Service '
                             'Group: "{1}" on VM node: "{2}", on Peer '
                             'node: "{3}"'
                             .format(vm_net["device_name"],
                                     lp_cs['name'],
                                     vm_nodes[node],
                                     sv_gp['nodes'][node]
                                     )
                             )
                    file_path = "{0}/ifcfg-{1}".format(
                        test_constants.NETWORK_SCRIPTS_DIR,
                        vm_net["device_name"])
                    cmd = '/bin/cat {0} | grep IPV6_DEFAULTGW'\
                          .format(file_path)
                    out, err, rc = self.run_command_via_node(
                        sv_gp['nodes'][node],
                        vm_nodes[node],
                        cmd)
                    self.assertEqual(0, rc)
                    self.assertEqual([], err)
                    self.assertNotEqual([], out)
                    out = out[0].split("=")[1]
                    self.assertEqual(
                        self._format_ipv6_to_list(vm_net['gateway6']),
                        self._format_ipv6_to_list(out))
                    # Default route address check
                    cmd = "/sbin/ip -6 route show dev {0} |"\
                            " awk 'NR == 3 {{print $3}}'"\
                            .format(vm_net["device_name"])
                    out, err, rc = self.run_command_via_node(
                        sv_gp['nodes'][node],
                        vm_nodes[node],
                        cmd)
                    self.assertTrue(vm_net['gateway6'] in out[0])

    def _check_vm_package(self, sv_gp):
        """
        Check the 'vm-package' type for a service group.
        """
        if 'vm-package' in sv_gp:
            pkg_list = []
            for pkg in sv_gp['vm-package']:
                pkg_list.append(pkg['name'])

            for node in sv_gp['nodes']:
                # Get the contents of the user-data file for the service group.
                data = self.get_file_contents(
                    sv_gp['nodes'][node], '/var/lib/libvirt/instances/{0}/'
                    'user-data'.format(sv_gp['vm-service']['service_name']))

                if not pkg_list:
                    break

                for pkg in pkg_list:
                    self.assertTrue(any(pkg in line for line in data))

    def _check_vm_yum_repo(self, sv_gp, lp_cs, vm_nodes):
        """
        Check the 'vm-yum-repo' type for a service group.
        """
        for node in sv_gp['nodes']:

            if 'vm-yum-repo' not in sv_gp:
                break

            if sv_gp['node-state'][sv_gp['nodes'][node]]:

                for repo in sv_gp['vm-yum-repo']:
                    self.log('info',
                             'Checking repo "{0}" for Service Group: '
                             '"{1}" on VM node: "{2}", on Peer node: "{3}"'
                             .format(repo['name'],
                                     lp_cs['name'],
                                     vm_nodes[node],
                                     sv_gp['nodes'][node]
                                     )
                             )

                    path = test_constants.YUM_CONFIG_FILES_DIR + '/' +\
                        repo['name'].lower() + '.repo'
                    cmd = '/bin/cat {0}'.format(path)
                    out, err, rc = self.run_command_via_node(
                        sv_gp['nodes'][node],
                        vm_nodes[node],
                        cmd)
                    self.assertEqual(0, rc)
                    self.assertEqual([], err)
                    self.assertTrue(
                        'baseurl = {0}'.format(repo['base_url']) in out)
                    # check repolist cmd output
                    print "=-------> ", repo['name']

    def _check_vm_alias(self, sv_gp, lp_cs, vm_nodes):
        """
        Check the 'vm-alias' type for a service group.
        """
        for node in sv_gp['nodes']:

            if 'vm-alias' not in sv_gp:
                break

            if sv_gp['node-state'][sv_gp['nodes'][node]]:

                cmd = self.net.get_cat_etc_hosts_cmd()
                out, err, rc = self.run_command_via_node(
                    sv_gp['nodes'][node], vm_nodes[node], cmd)
                self.assertEqual(0, rc)
                self.assertEqual([], err)

                self.log('info',
                         'Checking alias names for Service Group: '
                         '"{0}" on VM node: "{1}", on Peer node: "{2}"'
                         .format(lp_cs['name'],
                                 vm_nodes[node],
                                 sv_gp['nodes'][node]
                                 )
                         )
                for alias in sv_gp['vm-alias']:
                    # First check if the ip addres is in the list.
                    self.assertTrue(
                        any(alias['address'] in line for line in out))

                    # Now check if the alias names are configured for the
                    # ip address
                    for line in out:
                        if alias['address'] in line:
                            for name in alias['address'].split(','):
                                self.assertTrue(name in line)
                            continue

    def _check_vm_nfs_mount(self, sv_gp, lp_cs, vm_nodes):
        """
        Check the 'vm-nfs-mount' type for a service group
        """
        fstab_cmd = self.rhc.get_cat_cmd("/etc/fstab")
        mount_cmd = self.stor.get_mount_list_cmd()
        for node in sv_gp['nodes']:
            if 'vm-nfs-mount' not in sv_gp:
                break
            if sv_gp['node-state'][sv_gp['nodes'][node]]:
                self.log('info', 'Checking vm-nfs-mount for '
                         'Service Group: "{0}" on node: "{1}"'
                         .format(lp_cs['name'], sv_gp['nodes'][node]))
                fstab, stderr, return_code = \
                                self.run_command_via_node(sv_gp['nodes'][node],
                                                            vm_nodes[node],
                                                            fstab_cmd)
                self.assertEqual(return_code, 0)
                self.assertEqual(stderr, [], stderr)
                _, stderr, return_code = \
                                self.run_command_via_node(sv_gp['nodes'][node],
                                                            vm_nodes[node],
                                                            mount_cmd)
                self.assertEqual(return_code, 0)
                self.assertEqual(stderr, [], stderr)
                for nfs in sv_gp['vm-nfs-mount']:
                    # Check item props are in /etc/fstab file
                    found_mount = False
                    for line in fstab:
                        if nfs['device_path'] in line and \
                            nfs['mount_point'] in line and \
                            nfs['mount_options'] in line:
                            found_mount = True
                    # Check item props exist in /bin/mount cmd output
                    self.assertTrue(found_mount)

    def _check_vm_hostnames(self, sv_gp, lp_cs, vm_nodes):
        """
        Verify hostnames on nested VM
        """
        grep_cmd = "/bin/hostname"
        for node in sv_gp['nodes']:
            if sv_gp['node-state'][sv_gp['nodes'][node]]:
                self.log('info', 'Checking hostname for '
                             'Service Group: "{0}" on node: "{1}"'
                             .format(lp_cs['name'], sv_gp['nodes'][node]))
                stdout, stderr, rcode =\
                            self.run_command_via_node(sv_gp['nodes'][node],
                                                    vm_nodes[node],
                                                    grep_cmd)
                vm_hostname = stdout[0]
                self.assertEqual(rcode, 0)
                self.assertEqual(stderr, [], stderr)
                self.assertEqual(vm_hostname, vm_nodes[node],
                                    "Different hostnames found on the VM.")

    def _get_abv_tz_on_node(self, node, via_node=None):
        """
        Get the abbreviated timezone of a given node from the "date" command
        """
        cmd = "/bin/date"
        if via_node != None:
            out, err, r_code = self.run_command_via_node(via_node, node, cmd)
        else:
            out, err, r_code = self.run_command(node, cmd, su_root=True)
        self.assertNotEqual([], out)
        self.assertEqual([], err)
        self.assertEqual(0, r_code)
        # Example: "Thu Apr  9 15:48:53 IST 2015"
        date_cmd_regex = \
            r"^(?P<dow>\w+)\s(?P<month>\w+)\s+(?P<date>\d+)\s(?P<hour>\d+):"\
            r"(?P<minute>\d+):(?P<second>\d+)\s(?P<abv_tz>\w+)\s(?P<year>\d+)$"
        re_match = re.match(date_cmd_regex, out[0])
        re_dict = re_match.groupdict()
        return re_dict["abv_tz"]

    def _check_vm_timezone(self, sv_gp, lp_cs, vm_nodes):
        """
        For each VM, ensure that the timezone matches the
        timezone of the MS
        """
        ms_tz = self.get_timezone_on_node(self.ms_node)
        ms_avg_tz = self._get_abv_tz_on_node(self.ms_node)
        for node in sv_gp['nodes']:
            if sv_gp['node-state'][sv_gp['nodes'][node]]:
                self.log('info', 'Checking timezone for '
                         'Service Group: "{0}" on node: "{1}"'
                         .format(lp_cs['name'], sv_gp['nodes'][node]))
                vm_tz = self.get_timezone_on_node(vm_nodes[node],
                                        via_node=sv_gp['nodes'][node])
                vm_avg_tz = self._get_abv_tz_on_node(vm_nodes[node],
                                        via_node=sv_gp['nodes'][node])
                self.assertEqual(ms_tz, vm_tz)
                self.assertEqual(ms_avg_tz, vm_avg_tz)

    def _get_vm_dhcp_details(self, node, via_node=None, dhcp_nic=None):
        """
        Get the dhcp vm network config from a VM.
        Returns:
            dhcp network configuration
        """
        if dhcp_nic == None:
            self.log("info", "No Device supplied, searching VM for it")
            search_str = test_constants.NETWORK_SCRIPTS_DIR +\
                                " -type f -name *ifcfg-eth* "
            find_cmd = self.rhc.get_find_files_in_dir_cmd(search_str,
                                                            ["BOOTPROTO=dhcp"],
                                                            " -il")
            stdout, stderr, returnc = self.run_command_via_node(via_node,
                                                                node, find_cmd)
            self.assertNotEqual([], stdout)
            self.assertEqual([], stderr)
            self.assertEqual(0, returnc)
            dhcp_nic = stdout[0].rsplit('-', 1)[-1]
        self.log("info", "Checking IP from NIC {0} is in DHCP Range"\
                    .format(dhcp_nic))
        cmd = self.net.get_ifconfig_cmd(dhcp_nic, "-a")
        stdout, stderr, returnc = self.run_command_via_node(via_node,
                                                            node, cmd)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, returnc)
        dhcp_int = self.net.get_ifcfg_dict(stdout, dhcp_nic,
            os_ver=self.get_rhelver_used_on_node(node, via_node))
        return dhcp_int

    def _check_vm_dhcp(self, vm_node, node, lp_cs_name, device_name):
        """
        Description:
            For each vm dhcp network interface found in
            _check_vm_network_interface function, ensure its IP address
            is in dhcp service IPs range.
        """
        self.log('info', 'Checking DHCP for '
                     'Service Group: "{0}" on node: "{1}"'
                     .format(lp_cs_name, node))
        range_found = False
        for dhcp_range in self.dhcp_ranges:
            dhcp_range_props = self.get_props_from_url(self.ms_node,
                                                       dhcp_range)
            range_start = dhcp_range_props['start']
            range_end = dhcp_range_props['end']
            vm_dhcp_props = self._get_vm_dhcp_details(vm_node,
                    node, device_name)
            if self.net.is_ip_in_range(vm_dhcp_props['IPV4'],
                                        range_start, range_end):
                range_found = True
                break
        self.assertTrue(range_found, "Assigned IP is not in the range")

    @staticmethod
    def _get_vm_ip_map(service_groups, ip_map, act_hst,
                       stb_hst, node_hst):
        """
        Gets the ip map for VMs in the model.

        Args:
           service_groups (dict): Dictionary of vm service groups.

           ip_map (dict): The ip dict we are going to add to.

           act_hst (int): Number of active vms in current cluster.

           stb_hst (int): Number of standby vms in current cluster.

           node_hst(list): Number of nodes vms are run betwen.

        Builds a dict of the ipaddresses on the VMs on the current system.

        Returns:
           dict. Dictionary of ips of VMs.
        """
        for vm_net in service_groups['vm-network-interface']:
            ipaddr = []
            if 'ipaddresses' in vm_net:
                if vm_net['ipaddresses'] != "dhcp":
                    # CHECK NODE LIST MATCHES NUMBER OF IP ADDRESSES
                    ipaddr = vm_net['ipaddresses'].split(",")
                    ipv6addr = []
                if 'ipv6addresses' in vm_net:
                    # CHECK NODE LIST MATCHES NUMBER OF IPV6 ADDRESSES
                    ipv6addr = vm_net['ipv6addresses'].split(",")
                if int(act_hst) == 1 and int(stb_hst) == 1:
                    for node in ip_map:
                        if ipaddr != []:
                            ip_map[node]["ipv4"] = ipaddr[0]
                        if ipv6addr != []:
                            ip_map[node]["ipv6"] = ipv6addr[0]
                else:
                    for tlen in range(len(ip_map)):
                        if ipaddr != []:
                            ip_map[node_hst[tlen]]["ipv4"] = ipaddr[tlen]
                        if ipv6addr != []:
                            ip_map[node_hst[tlen]]["ipv6"] = ipv6addr[tlen]

        return ip_map

    def _add_vm_nodes_connection_details(self, service_groups):
        """
        Build a list of all connection details for each node and add to
        utils node_list.
        """

        # CREATE VM NETWORK MAPPING (NOT USING THE LITP EXPOSED PROPERTY)
        node_template = {'hostname': None, 'ipv4': None, 'ipv6': None}
        ip_map = {}
        index_sg = 0
        for sv_gp in service_groups:
            node_template = {'hostname': None, 'ipv4': None, 'ipv6': None}
            ip_map = {}
            node_hst = sv_gp['vcs-clustered-service']['node_list'].split(",")
            act_hst = sv_gp['vcs-clustered-service']['active']
            stb_hst = sv_gp['vcs-clustered-service']['standby']
            total_hst = int(act_hst) + int(stb_hst)
            self.assertEqual(len(node_hst), total_hst)
            for node in node_hst:
                ip_map[node] = node_template.copy()
            sg_hsts = None
            if 'hostnames' in sv_gp['vm-service']:
                sg_hsts = sv_gp['vm-service']['hostnames'].split(",")
            else:
                if int(stb_hst) != 1:
                    sg_hsts = []
                    for node in node_hst:
                        print node
                        print sg_hsts
                        print sv_gp['vm-service']['service_name'].split(",")[0]
                        sg_hsts.append("{0}-{1}".format(node,
                              sv_gp['vm-service']['service_name'].\
                                    split(",")[0]))
                else:
                    sg_hsts = sv_gp['vm-service']['service_name'].split(",")
            if int(act_hst) == 1 and int(stb_hst) == 1:
                for node in ip_map:
                    ip_map[node]["hostname"] = sg_hsts[0]
            else:
                for tlen in range(len(ip_map)):
                    ip_map[node_hst[tlen]]["hostname"] = sg_hsts[tlen]
            service_groups[index_sg]["nodes-hostnames"] = {}
            for nl_node in ip_map:
                service_groups[index_sg]["nodes-hostnames"][nl_node] \
                        = ip_map[nl_node]["hostname"]
            index_sg += 1

            ip_map = self._get_vm_ip_map(sv_gp, ip_map,
                                         act_hst, stb_hst,
                                         node_hst)
            ##
            #service_groups[sv_gp["nodes_hostnames"]]
            for node in ip_map:
                self.log("info", "VMHOSTCONNSET: {0} IPV4: {1} IPV6: {2}"\
                        .format(ip_map[node]['hostname'],
                        ip_map[node]['ipv4'], ip_map[node]['ipv6'], node))
                self.add_vm_to_nodelist(
                    ip_map[node]['hostname'],
                    ip_map[node]['ipv4'],
                    test_constants.LIBVIRT_VM_USERNAME,
                    test_constants.LIBVIRT_VM_PASSWORD,
                    ipv6=ip_map[node]['ipv6']
                )
        self._print_list(0, service_groups)

    @attr('all', 'revert', 'system_check', 'vcs_vm', 'vcs_vm_tc01')
    def test_01_p_verify_vm_vcs_clustered_service(self):
        """
        Description:
            Test all parts of a Service Group that runs on a virtual machine.
            This test covers the following item types:
                * vm-image
                * vm-service
                * vcs-clustered-service
                * vm-package
                * vm-alias
                * vm-nfs-mount
                * vm-network-interface
                * vm-yum-repo
                * vm-ssh-key

        Actions:
            1. Get all vm service groups in the model.
            2. Gather connection details for vm_nodes.
            3. For each vm service group:
                a. Gather information about the service group(hares, hastat,
                hagrp)
                b. Check the 'vcs-clustered-service' type
                c. Check the 'vm-service' type
                d. Check the 'vm-image' type
                e. Check the 'vm-network-interface' type
                f. Check the 'vm-ssh-key' type
                g. Check the 'vm-package' type
                h. Check the 'vm-yum-repo' type
                i. Check the 'vm-alias' type
        """

        # 1. Get all vm service groups in the model.
        service_groups = self.get_vcs_vm_model_info()

        # 2: Gather connection details for vm_nodes.
        self._add_vm_nodes_connection_details(service_groups)
        self.dhcp_ranges = self.find(self.ms_node, '/software/services',
                                    'dhcp-range', assert_not_empty=False)

        # 3. For each vm service group:
        for sv_gp in service_groups:
            # Some naming convention for this method:
            #   lp_*  : A value that comes from the Litp model.
            #   v_*   : A value that comes from VCS.
            #   sv    : service
            #   pt    : path
            #   nm    : name
            #   sv_gp : service group
            #   cs    : clustered service
            #   cl    : cluster
            #   hns   : hostnames

            # Litp clustered service dict.
            lp_cs = sv_gp['vcs-clustered-service']
            lp_cs_id = lp_cs['url'].split('/')[-1]
            # Litp clustered service name: FO_SG_vm1
            lp_cs_nm = lp_cs['name']
            # Litp clustered service id: vmservice2
            lp_cl_id = sv_gp['cluster']['id']
            lp_sv_id = sv_gp['vm-service']['url'].split('/')[-1]

            # VCS clustered service name : 'Grp_CS_c1_FO_SG_vm1'
            v_cs_nm = self.vcs.generate_clustered_service_name(lp_cs_id,
                                                               lp_cl_id)
            # VCS application resource name : 'Res_App_c1_FO_SG_vm1_vmservice2'
            v_rs_nm = self.vcs.generate_application_resource_name(lp_cs_nm,
                                                                  lp_cl_id,
                                                                  lp_sv_id)
            # VCS and Litp node names - VCS: n1, Litp: node1
            # Commands only need to run on one node so just pop one from list
            v_nd, lp_nd = sv_gp['nodes'].popitem()
            sv_gp['nodes'][v_nd] = lp_nd

            # a. Gather information about the service group(hares, hastat,
            #    hagrp)
            hastat = self.run_vcs_hastatus_sum_command(lp_nd)
            hares = self.run_vcs_hares_display_command(lp_nd, v_rs_nm)
            hagrp = self.run_vcs_hagrp_display_command(lp_nd, v_cs_nm)

            vm_nd_hns = sv_gp["nodes-hostnames"]

            # b. Check the 'vcs-clustered-service' type
            self._check_vcs_clustered_service(sv_gp, lp_cs_nm, lp_nd, lp_cs,
                                              v_cs_nm, hares, hagrp, hastat)

            # c. Check the 'vm-service' type
            self._check_vm_service(sv_gp, hares, vm_nd_hns)

            # d. Check the 'vm-image' type
            image = sv_gp['vm-image']
            # get locations on ms for image
            vm_image_ms = test_constants.VM_IMAGE_MS_DIR + "/" \
                    + image['source_uri'].split("/")[-1]
            # get md5sum on ms for image
            outp, err, rc = self.run_command(self.ms_node,
                    "/usr/bin/md5sum {0}".format(vm_image_ms))
            self.assertEqual(0, rc)
            self.assertEqual([], err)
            self.assertNotEqual([], outp)
            msmd5sum = outp[0].split()[0]
            # get locations on nodes for image
            vm_image_nd = test_constants.LIBVIRT_IMAGE_DIR + "/" \
                    + image['source_uri'].split("/")[-1]
            for node in sv_gp['nodes']:
                self.log('info', 'Checking vm-image source_uri for Service '
                         'Group: "{0}" on node: "{1}"'
                         .format(lp_cs['name'], sv_gp['nodes'][node]))
                self.assertTrue(
                            self.check_repo_url_exists(sv_gp['nodes'][node],
                            image['source_uri']))
                # get md5sum on node for image
                outp, err, rc = self.run_command(sv_gp['nodes'][node],
                    "/usr/bin/md5sum {0}".format(vm_image_nd))
                self.assertEqual(0, rc)
                self.assertEqual([], err)
                self.assertNotEqual([], outp)
                ndmd5sum = outp[0].split()[0]
                # compare node and ms md5checksum
                self.assertEqual(msmd5sum, ndmd5sum)

            # e. Check the 'vm-network-interface' type
            self._check_vm_network_interface(sv_gp, lp_cs, vm_nd_hns)

            # g. Check the 'vm-package' type
            self._check_vm_package(sv_gp)

            # h. Check the 'vm-yum-repo' type
            self._check_vm_yum_repo(sv_gp, lp_cs, vm_nd_hns)

            # i. Check the 'vm-alias' type
            self._check_vm_alias(sv_gp, lp_cs, vm_nd_hns)

            # j. Check the 'vm-nfs-mount' type
            self._check_vm_nfs_mount(sv_gp, lp_cs, vm_nd_hns)

            # k. Check vm hostnames
            self._check_vm_hostnames(sv_gp, lp_cs, vm_nd_hns)

            # l. Check that VM timezones are equal to MS timezone
            self._check_vm_timezone(sv_gp, lp_cs, vm_nd_hns)
