"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2016
@author:    Bryan O'Neill
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from networking_utils import NetworkingUtils
from vcs_utils import VCSUtils
from storage_utils import StorageUtils
import test_constants
import simplejson


class MSVM(GenericTest):
    """
    Test the VM services on the LITP Management Server.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(MSVM, self).setUp()

        self.ms_node = self.get_management_node_filename()
        self.rhc = RHCmdUtils()
        self.vcs = VCSUtils()
        self.net = NetworkingUtils()
        self.stor = StorageUtils()

    def tearDown(self):
        """ Teardown run after every test """

        super(MSVM, self).tearDown()

    def get_ms_vm_model_info(self):
        """
        Get all information about the VM Services running on the MS.
        This information
        """

        vm_service_list = []

        type_list = ['vm-alias', 'vm-yum-repo', 'vm-package',
                     'vm-network-interface', 'vm-ssh-key', 'vm-service']
        prop_dict = {}
        infra_dict = {}

        urls = self.find(self.ms_node, '/software', 'vm-image',
                         assert_not_empty=False)
        for url in urls:
            props = self.get_props_from_url(self.ms_node, url)
            prop_dict['url'] = url
            for prop in props:
                prop_dict[prop] = props[prop]
            infra_dict[props['name']] = prop_dict

        services = self.find(self.ms_node, "/ms/services/", "vm-service",
                             assert_not_empty=False)

        for vm_serv in services:
            vm_service_dict = {}
            prop_dict = {}
            for itype in type_list:
                urls = self.find(self.ms_node, vm_serv, itype,
                                 assert_not_empty=False)
                for url in urls:
                    props = self.get_props_from_url(self.ms_node, url)
                    prop_dict['url'] = url
                    prop_dict.update(props)

                    if itype in vm_service_dict:
                        vm_service_dict[itype].append(prop_dict)
                    else:
                        if itype == 'vm-service':
                            vm_service_dict[itype] = prop_dict
                        else:
                            vm_service_dict[itype] = []
                            vm_service_dict[itype].append(prop_dict)
                    prop_dict = {}

            vm_image_name = vm_service_dict['vm-service']['image_name']
            vm_service_dict['vm-image'] = infra_dict[vm_image_name]

            vm_service_list.append(vm_service_dict)

        self._print_list(0, vm_service_list)
        return vm_service_list

    def _check_vm_service(self, service, host):
        """
        Check the vm-service type for a MS VM Service
        """

        self.log('info', 'Checking vm-service properties for VM Service:'
                         ' "{0}" on host node: "{1}"'
                         .format(service['service_name'], host))

        # Get dominfo for service, from this check cpus, memory
        cmd = '/usr/bin/virsh dominfo {0}'.format(service['service_name'])
        out, err, rc = self.run_command(self.ms_node, cmd, su_root=True)
        self.assertEqual(0, rc)
        self.assertEqual([], err)
        self.assertNotEqual([], out)
        dominfo = {}
        for line in out:
            line = line.split(':')
            dominfo[line[0]] = line[1].strip(' ')

        # Check adaptor version
        self.log('info',
                 'Check adaptor version for VM Service: "{0}" on host '
                 'node: "{1}"'.format(service['service_name'], host))
        cmd = self.rhc.check_pkg_installed(
            ['ERIClitpmnlibvirt_CXP9031529-{0}'
             .format(service['adaptor_version'])])
        out, err, rc = self.run_command(self.ms_node, cmd)
        self.assertEqual(0, rc)
        self.assertEqual([], err)
        self.assertNotEqual([], out)

        # Check cpus
        self.log('info',
                 'Check number of cpus for VM Service: "{0}" on host '
                 'node: "{1}"'.format(service['service_name'], host))
        self.assertEqual(service['cpus'], dominfo['CPU(s)'])

        # Check memory
        self.log('info',
                 'Check memory for VM Service: "{0}" on host '
                 'node: "{1}"'.format(service['service_name'], host))
        dominfo['Max memory'] = dominfo['Max memory'].split(' ')[0]
        service['ram'] = service['ram'].strip('M')
        v_ram = str(int(dominfo['Max memory']) / 1024)
        self.assertEqual(service['ram'], v_ram)

        # Check if tuned is installed on host node
        self.log('info',
                 'Check "tuned" is installed for VM Service: "{0}" on host '
                 'node: "{1}"'.format(service['service_name'], host))
        cmd = self.rhc.check_pkg_installed(['tuned'])
        out, err, rc = self.run_command(self.ms_node, cmd)
        self.assertEqual([], err)
        self.assertNotEqual([], out)
        self.assertEqual(0, rc)

        # Check if tuned is running
        self.log('info',
                 'Check "tuned" is running for VM Service: "{0}" on '
                 'node: "{1}"'.format(service['service_name'], self.ms_node))
        self.get_service_status(self.ms_node, 'tuned')

    def _check_vm_network_interface(self, service, host, vm_node):
        """
        Check the vm-network-interface type for a VM service
        """
        node_rh_ver = self.get_rhelver_used_on_node(vm_node, host)
        cmd = self.net.get_ifconfig_cmd()
        out, err, rc = self.run_command_via_node(host, vm_node, cmd)
        self.assertEqual(0, rc)
        self.assertEqual([], err)
        self.assertNotEqual([], out)
        ifconfig = out

        for vm_net in service['vm-network-interface']:
            ip_map = {}
            ip_map = self.get_ip_map(vm_net, host)

            service_name = service['vm-service']['service_name']

            # Chech eth is up
            cmd = "/sbin/ifconfig | grep -E '^{0} |^{0}:'"\
                  .format(vm_net["device_name"])
            out, err, rc = self.run_command_via_node(host, vm_node, cmd)

            self.log('info',
                     'Checking eth: "{0}" UP for VM Service: '
                     '"{1}" on VM: "{2}", on host node: "{3}"'
                     .format(vm_net["device_name"], service_name,
                             vm_node, host)
                     )
            self.assertEqual(0, rc)
            self.assertEqual([], err)
            self.assertNotEqual([], out)

            ifcfg_dict = self.net.get_ifcfg_dict(ifconfig,
                                                 vm_net["device_name"],
                                                 os_ver=node_rh_ver)

            # Check correct mac prefix if supplied.
            if 'mac_prefix' in vm_net:
                self.log('info', 'Checking mac prefix "{0}" on eth: '
                         '"{1}" for VM Service: "{2}" on VM: '
                         '"{3}", on host node: "{4}"'
                         .format(vm_net['mac_prefix'],
                                 vm_net["device_name"],
                                 service_name,
                                 vm_node, host)
                         )
                self.assertTrue(
                    ifcfg_dict["MAC"].lower().startswith(
                        vm_net['mac_prefix'].lower())
                )

            if 'ipv4' in ip_map[host]:
                self.log('info', 'Checking ipv4 address "{0}" on eth: '
                         '"{1}" for VM Service: "{2}" on VM: '
                         '"{3}", on host node: "{4}"'
                         .format(ip_map[host]['ipv4'],
                                 vm_net["device_name"],
                                 service_name,
                                 vm_node, host)
                         )
                self.assertEqual(ip_map[host]['ipv4'],
                                 self.net.get_ipv4_from_dict(ifcfg_dict))
            if 'ipv6' in ip_map[host]:
                self.log('info', 'Checking ipv6 address "{0}" on eth: '
                         '"{1}" for VM Service: "{2}" on VM: '
                         '"{3}", on host node: "{4}"'
                         .format(ip_map[host]['ipv6'],
                                 vm_net["device_name"],
                                 service_name,
                                 vm_node, host)
                         )
                ip6_addrs = self.net.get_ipv6_from_dict(ifcfg_dict)
                ipv6 = self.format_ipv6_to_list(ip_map[host]['ipv6'])
                self.assertTrue(
                    any(ipv6 == self.format_ipv6_to_list(ip)
                        for ip in ip6_addrs))

            if 'gateway' in vm_net:
                self.log('info',
                         'Checking eth: "{0}" gateway for VM Service: "{1}"'
                         ' on VM: "{2}", on host node: "{3}"'
                         .format(vm_net["device_name"],
                                 service_name,
                                 vm_node, host)
                         )
                file_path = "{0}/ifcfg-{1}".format(
                    test_constants.NETWORK_SCRIPTS_DIR,
                    vm_net["device_name"])
                cmd = '/bin/cat {0} | grep GATEWAY={1}'.format(
                    file_path, vm_net['gateway'])
                out, err, rc = self.run_command_via_node(host, vm_node, cmd)
                self.assertEqual(0, rc)
                self.assertEqual([], err)
                self.assertNotEqual([], out)

            if 'gateway6' in vm_net:
                self.log('info',
                         'Checking eth: "{0}" gateway6 for VM Service: "{1}"'
                         ' on VM: "{2}", on host node: "{3}"'
                         .format(vm_net["device_name"],
                                 service_name,
                                 vm_node, host)
                         )
                file_path = "{0}/ifcfg-{1}".format(
                    test_constants.NETWORK_SCRIPTS_DIR,
                    vm_net["device_name"])
                cmd = '/bin/cat {0} | grep IPV6_DEFAULTGW'\
                      .format(file_path)
                out, err, rc = self.run_command_via_node(host, vm_node, cmd)
                self.assertEqual(0, rc)
                self.assertEqual([], err)
                self.assertNotEqual([], out)
                out = out[0].split("=")[1]
                self.assertEqual(
                    self.format_ipv6_to_list(vm_net['gateway6']),
                    self.format_ipv6_to_list(out))

    def _check_vm_ssh_key(self, service, host, vm_node):
        """
        Check the 'vm-ssh-key' type for a VM service.
        """

        if 'vm-ssh-key' not in service:
            return True

        self.log('info', 'Checking vm-ssh-key for VM Service: '
                         '"{0}", on VM: "{1}", on host node '
                         '"{2}"'.format(service['vm-service']['service_name'],
                                        vm_node, host))
        cmd = '/bin/cat /root/.ssh/authorized_keys'
        out, err, rc = self.run_command_via_node(host, vm_node, cmd)
        self.assertEqual(0, rc)
        self.assertEqual([], err)
        for key in service['vm-ssh-key']:
            self.assertTrue(
                any(key['ssh_key'] in line for line in out))

    def _check_vm_package(self, service, node):
        """
        Check the 'vm-package' type for a VM service.
        """
        pkg_list = []
        if 'vm-package' in service:
            for pkg in service['vm-package']:
                pkg_list.append(pkg['name'])

        # Get the contents of the user-data file for the service group.
        data = self.get_file_contents(
            node, '/var/lib/libvirt/instances/{0}/'
            'user-data'.format(service['vm-service']['service_name']))

        for pkg in pkg_list:
            self.assertTrue(any(pkg in line for line in data))

    def _check_vm_yum_repo(self, service, host, vm_node):
        """
        Check the 'vm-yum-repo' type for a VM service.
        """

        if 'vm-yum-repo' not in service:
            return True

        for repo in service['vm-yum-repo']:
            self.log('info',
                     'Checking repo "{0}" for VM Service: '
                     '"{1}" on VM: "{2}", on host node: "{3}"'
                     .format(repo['name'],
                             service['vm-service']['service_name'],
                             vm_node, host)
                     )

            path = test_constants.YUM_CONFIG_FILES_DIR + '/' +\
                repo['name'].lower() + '.repo'
            cmd = '/bin/cat {0}'.format(path)
            out, err, rc = self.run_command_via_node(host, vm_node, cmd)
            self.assertEqual(0, rc)
            self.assertEqual([], err)
            self.assertTrue(
                'baseurl = {0}'.format(repo['base_url']) in out)

    def _check_vm_alias(self, service, host, vm_node):
        """
        Check the 'vm-alias' type for a VM service.
        """

        if 'vm-alias' not in service:
            return True

        self.log('info',
                 'Checking alias names for VM Service: '
                 '"{0}" on VM: "{1}", on host node: "{2}"'
                 .format(service['vm-service']['service_name'], vm_node, host)
                 )

        cmd = self.net.get_cat_etc_hosts_cmd()
        out, err, rc = self.run_command_via_node(host, vm_node, cmd)
        self.assertEqual(0, rc)
        self.assertEqual([], err)

        for alias in service['vm-alias']:
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

    def _add_vm_nodes_connection_details(self, vm_model):
        """
        Build a list of all connection details for each node and add to
        utils node_list.
        """
        node_template = {'hostname': None, 'ipv4': None, 'ipv6': None}
        for service in vm_model:
            vm_nodes = {}
            hst_map = \
                simplejson.loads(service['vm-service']['node_hostname_map']
                                 .replace("'", '"'))

            for node in hst_map:
                vm_nodes[node] = node_template.copy()

                vm_nodes[node]['hostname'] = hst_map[node]

                for vm_net in service['vm-network-interface']:
                    ip_dict = simplejson.loads(
                        vm_net['node_ip_map'].replace("'", '"'))
                    if node in ip_dict:
                        if 'ipv4' in ip_dict[node]:
                            vm_nodes[node]['ipv4'] = ip_dict[node]['ipv4']
                        if 'ipv6' in ip_dict[node]:
                            vm_nodes[node]['ipv6'] = ip_dict[node]['ipv6']

                    if vm_nodes[node]['ipv6'] and vm_nodes[node]['ipv4']:
                        break

            for node in vm_nodes:
                self.add_vm_to_nodelist(
                    vm_nodes[node]['hostname'],
                    vm_nodes[node]['ipv4'],
                    test_constants.LIBVIRT_VM_USERNAME,
                    test_constants.LIBVIRT_VM_PASSWORD,
                    ipv6=vm_nodes[node]['ipv6']
                )

    @staticmethod
    def get_ip_map(vm_net, node_hst):
        """
        Populate IP MAP dictionary
        """
        ip_map = {node_hst: {}}
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
        if ipaddr:
            if len(ipaddr) == 1:
                ipaddr = ipaddr[0]
            ip_map[node_hst]['ipv4'] = ipaddr
        if ipv6addr:
            if len(ipv6addr) == 1:
                ipv6addr = ipv6addr[0]
            ip_map[node_hst]['ipv6'] = ipv6addr
        return ip_map

    @staticmethod
    def format_ipv6_to_list(ipv6_addr, remove_prefix=True):
        """
        This function takes an IPv6 address as a string and returns a list
        containing 8 elements. Each element is a decimal number respective to
        each hexadecimal segment of the address.
        If a network prefix is included in the address and the remove_prefix
        KWarg is ser False this will be appended to the list as the 9th
        element.

        Args:
            ipv6_addr (str): The IPv6 address, with or without prefix

        KWargs:
            remove_prefix (bool): Option to remove a prefix from the address.

        Returns:
            list. The IPv6 address as a list.
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

        if prefix and not remove_prefix:
            ret_ip.append(int(prefix, 10))

        return ret_ip

    @attr('all', 'revert', 'system_check', 'ms_vm', 'ms_vm_tc01')
    def test_01_p_verify_ms_vm_service(self):
        """
        Description:
            Test all VM services on the MS of a LITP deployment.
            This test covers the following item types:
                * vm-service
                * vm-image
                * vm-package
                * vm-alias
                * vm-network-interface
                * vm-yum-repo
                * vm-ssh-key

        Actions:
            1. Get all VM services modelled on the MS
            2. For each VM service on the MS:
                a. Check the 'vm-service' type
                b. Check the 'vm-image' type
                c. Check the 'vm-network-interface' type
                d. Check the 'vm-ssh-key' type
                e. Check the 'vm-package' type
                f. Check the 'vm-yum-repo' type
                g. Check the 'vm-alias' type
        """

        # 1. Get all VM services modelled on the MS
        vm_model = self.get_ms_vm_model_info()
        self._add_vm_nodes_connection_details(vm_model)

        # 2. For each VM service on the MS
        for msvm in vm_model:

            service = msvm['vm-service']
            image = msvm['vm-image']
            hst_map = simplejson.loads(service['node_hostname_map']
                                       .replace("'", '"'))
            vm_node = str
            for key in hst_map:
                # Get the hostname of the VM
                vm_node = hst_map[key]

            # a. Check the 'vm-service' type
            self._check_vm_service(service, self.ms_node)

            # b. Check the 'vm-image' type
            self.log('info', 'Checking vm-image source_uri for VM Service:'
                     ' "{0}" on node: "{1}"'
                     .format(service['service_name'], self.ms_node))
            self.assertTrue(self.check_repo_url_exists(self.ms_node,
                                                       image['source_uri']))

            # c. Check the 'vm-network-interface' type
            self._check_vm_network_interface(msvm, self.ms_node, vm_node)

            # d. Check the 'vm-ssh-key' type
            self._check_vm_ssh_key(msvm, self.ms_node, vm_node)

            # e. Check the 'vm-package' type
            self._check_vm_package(msvm, self.ms_node)

            # f. Check the 'vm-yum-repo' type
            self._check_vm_yum_repo(msvm, self.ms_node, vm_node)

            # g. Check the 'vm-alias' type
            self._check_vm_alias(msvm, self.ms_node, vm_node)
