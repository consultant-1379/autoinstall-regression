"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     July 2015
@author:    Laura Forbes
"""

from litp_generic_test import GenericTest, attr
from storage_utils import StorageUtils
import test_constants
import re


class Nas(GenericTest):
    """
    Test the 'nas_extension' LITP item type.
    Item Types verified are 'nfs-mount', 'nfs-service',
        'sfs-virtual-server', 'sfs-service', 'sfs-pool',
            'sfs-cache', 'sfs-filesystem', and 'sfs-export'.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(Nas, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])
        self.storage = StorageUtils()

    def tearDown(self):
        """ Teardown run after every test """

        super(Nas, self).tearDown()

    def _mount_checks(self, nfs_serv, sfs_services, sfs_virt, provider,
                      export_path, node_name, mount_point, mount_options):
        """
        Description:
            Runs 'mount' command on node and checks that the ipv4address,
            export_path, mount_point, and mount_options properties match
            in the model.

        Args:
            nfs_serv (list): List of paths to nfs-service items in the model.
            sfs_services (list): List of paths to sfs-service items in model.
            sfs_virt (list): Paths to sfs-virtual-server items in the model.
            provider (str): 'provider' property from nfs-mount.
            export_path (str): 'export_path' property from nfs-mount.
            node_name (str): Name of the node to execute 'mount' on.
            mount_point (str): 'mount_point' property from nfs-mount.
            mount_options (str): 'mount_options' property from nfs-mount.

        Actions:
            For each path:
                a. Get the properties of the path.
                If 'name' property matches 'provider' property from nfs-mount:
                    b. Run a 'mount' command on node, grepping the export_path.
                    c. Assert that there are no errors running the command.
                    d. Ensure ipv4address, mount_point and mount_options are
                                            present in returned 'mount' output.
        """
        url_paths = []
        if nfs_serv:
            url_paths.extend(nfs_serv)
        else:
            self.log("info", "No nfs-service item "
                             "type found on {0}.".format(node_name))
        if sfs_services:
            url_paths.extend(sfs_services)
        else:
            self.log("info", "No sfs-service item "
                             "type found on {0}.".format(node_name))
        if sfs_virt:
            url_paths.extend(sfs_virt)
        else:
            self.log("info", "No sfs-virtual-server item "
                             "type found on {0}.".format(node_name))

        # For each path passed in:
        for path in url_paths:
            # a. Get the properties of the path
            props = self.get_props_from_url(self.ms_node, path)
            # If 'name' property matches 'provider' property from nfs-mount:
            if props['name'] == provider:
                if 'ipv4address' in props:
                    ip_add = props['ipv4address']
                # nfs-service may have an ipv6address property:
                elif 'ipv6address' in props:
                    ip_add = props['ipv6address']

                # b. Run 'mount' command on the node, grepping the export_path
                mount_cmd = self.storage.get_mount_list_cmd(
                    grep_item=export_path)
                mount_out, stderr, rc = self.run_command(node_name, mount_cmd)
                # c. Assert that there are no errors running the command
                self.assertNotEqual([], mount_out)
                self.assertEqual([], stderr)
                self.assertEqual(0, rc)

                # d. Ensure ipv4address, mount_point and mount_options are
                #                           present in returned 'mount' output
                self.assertTrue(ip_add in mount_out[0],
                    "IP {0} does not match mount on {1} for {2}:\n{3}".format(
                        ip_add, node_name, export_path, mount_out[0]))
                self.assertTrue(mount_point in mount_out[0], "mount_point {0} "
                    "does not match mount on {1} for {2}:\n{3}".format(
                        mount_point, node_name, export_path, mount_out[0]))
                self.assertTrue(mount_options in mount_out[0], "mount_options "
                    "{0} do not match mount on {1} for {2}:\n{3}".format(
                        mount_options, node_name, export_path, mount_out[0]))

    def _sfs_services(self, path):
        """
        Description:
            If the sfs-service 'user_name' property is defined, ensure that
                it is not set to 'master'.
            If the sfs-service 'user_name' property is defined, ensure the
                'password_key' property is also defined.

        Args:
            path (str): The path to the sfs-service item type in the model.

        Actions:
            a. Create dictionary to contain the properties of the path passed.
            If 'user_name' property is defined:
                b. Ensure it is not set to 'master'.
                c. Ensure 'password_key' property is defined.
        """
        # a. Create a dictionary to contain the properties of the path passed
        prop_sfs_service = self.get_props_from_url(self.ms_node, path)

        if 'user_name' in prop_sfs_service:
            # b. Value of user_name property must not be 'master'
            self.assertTrue(prop_sfs_service['user_name'] != "master",
                        "sfs-service: Value of user_name must not be 'master'")

            # c. Ensure 'password_key' property is defined
            self.assertTrue('password_key' in prop_sfs_service,
                    "sfs-service username defined, but no password defined")

    def _sfs_filesystem(self, filesystem_size, filesystem_path, sfs_node,
                        pool_name, node_name, mount_point, filesystem_prop,
                        sfs_cache, cache_name):
        """
        Description:
            Ensure file path specified in model exists on SFS node and
                    matches size defined.
            Check that 'mount_point' property exists on node.
            Test 'cache_name' property.

        Args:
            filesystem_size (str): sfs-filesystem 'size' property value.
            filesystem_path (str): Path to sfs-filesystem item type the model.
            sfs_node (str): Name of the SFS node.
            pool_name (str): sfs-pool 'name' property value.
            node_name (str): Name of the node to execute 'mount' on.
            mount_point (str): 'mount_point' property from nfs-mount.
            filesystem_prop (dict): Properties of sfs-filesystem path.
            sfs_cache (list): List of sfs-cache paths under sfs-pool.
            cache_name (str): sfs-cache 'name' property value.

        Actions:
            a. Extract the number from filesystem_size.
            b. Ensure 'path' property exists on SFS node and
                        matches size defined in model.
            c. Check that 'mount_point' property exists on node.
            d. Test that both cache_name and snap_size exist, or
                        neither exist (i.e. XNOR).
            If they exist:
                e. Ensure sfs-cache 'cache_name' property exists.
                f. Match sfs-cache 'name' property with
                            sfs-filesystem 'filesystem_cache' property.

        """
        # a. Extract the number from filesystem_size
        dir_size = (re.findall("\\d+", filesystem_size))[0]

        # b. Ensure 'path' property exists on SFS and matches size in model
        self.log("info", "Checking if {0} exists on SFS {1}.".format(
                                                filesystem_path, sfs_node))

        self.assertTrue(self.is_sfs_filesystem_present(sfs_node,
            filesystem_path.split("/")[2], size=dir_size, pool=pool_name),
            "Either {0} defined in model does not exist on SFS '{1}' or "
            "size does not match model".format(filesystem_path, sfs_node))

        # c. Check that 'mount_point' property exists on node
        self.assertTrue(self.remote_path_exists(node_name,
            mount_point, expect_file=False), "Path {0} does "
                "not exist on {1}.".format(mount_point, node_name))

        # d. Test that both cache_name and snap_size exist, or neither exist.
        #       If you specify a value for the snap_size property, you must
        #       define a value for the cache_name property (and vice versa).
        if 'cache_name' in filesystem_prop or 'snap_size' in filesystem_prop:
            self.assertTrue('cache_name' in filesystem_prop and 'snap_size' in
                filesystem_prop, "If a value for snap_size is specified, a "
                "value for cache_name must also be specified and vice versa.")

            # If you define an sfs-cache item type in the model, you must
            #   also define the cache_name and snap_size properties of
            #       at least one sfs-filesystem item

            # e. Ensure sfs-cache 'cache_name' property exists
            self.assertTrue(sfs_cache, "sfs-cache item must be defined if "
                "sfs-filesystem 'cache_name' and 'snap_size' properties are "
                    "defined in sfs-filesystem.")

            # f. Match sfs-cache 'name' property with
            #       sfs-filesystem 'filesystem_cache' property
            self.assertEqual(cache_name, filesystem_prop['cache_name'],
                "Cache names in sfs-cache and sfs-filesystem do not "
                    "match --> {0} != {1}".format(
                        cache_name, filesystem_prop['cache_name']))

    def _sfs_export(self, sfs_export, sfs_node, sfs_path):
        """
        Description:
            Match SFS file path, IPs and user options on model with SFS node.

        Args:
            sfs_export (str): Path to sfs-export item type in the model.
            sfs_node (str): Name of the SFS node.
            sfs_path (str): Path to the filesystem directory
                                            defined in sfs-filesystem.

        Actions:
            a. Create a dictionary to contain properties of the passed path.
            b. Split 'ipv4allowed_clients' property value into individual IPs.
            For each IP:
                c. Match the IP and user options on the model and SFS
                    on the given SFS path.
        """
        # a. Create a dictionary to contain properties of the passed path
        prop_export = (self.get_props_from_url(self.ms_node, sfs_export))

        # b. Split the 'ipv4allowed_clients' property value into individual IPs
        ipv4_clients = prop_export['ipv4allowed_clients']
        ipv4_clients = ipv4_clients.split(",")
        export_options = prop_export['options']

        for ipv4 in ipv4_clients:
            # c. Match SFS file path, IPs and user options on model with SFS
            self.assertTrue(self.is_sfs_share_present(sfs_node, sfs_path,
                ip_add=ipv4, perm=export_options), "ipv4allowed_clients "
                            "and options do not match on model and SFS.")

    def get_sfs_node_from_vip1(self, sfs_vip1):
        """
        Get an SFS server by its vip1 address

        Args:
            sfs_vip1 (str): The vip1 address to match

        Returns:
            str. SFS node which matches the given vip1 address

        Raises:
            AssertionError: If no matching SFS node found
        """
        sfs_node = None
        node_type = "sfs"
        for node in self.nodes:
            if node_type == node.nodetype and sfs_vip1 == node.vips.get('1'):
                sfs_node = node.filename

        self.assertNotEqual(sfs_node, None, "No SFS node found")

        return sfs_node

    @attr('all', 'revert', 'system_check', 'nas', 'nas_tc01')
    def test_01_p_nas(self):
        """
        Description:
            Test that all managed filesystems match
                    in the model and in the SFS server(s).
        Actions:
            For each node:
                1. Check for any modelled 'nfs-mount' items on node.
                For each path of type 'nfs-mount':
                    2. Get the properties of the path.
                    3. Check for any modelled 'nfs-service' items.
                    4. Check for any modelled 'sfs-service' items.
                    5. Check for any modelled 'sfs-virtual-server' items.
                    6. Run 'mount' command on node to compare 'nfs-mount'
                            properties and 'ipv4address' property from any
                                nfs-service, sfs-service and sfs-virtual-server
                                    paths found.
                    For each path of type 'sfs-virtual-server':
                    7. Get the properties of the path.
                    8. If sfs-virtual-server 'name' property matches nfs-mount
                        'provider' property, update connection data of SFS node
                    For each path of type 'sfs-service':
                    If the 'sfs-service' item parents the
                            'sfs-virtual-server' being tested:
                        9.Test sfs-service 'user_name' property.
                        10. Check for any modelled 'sfs-pool' items under
                                the sfs-service path.
                        For each path of type 'sfs-pool':
                            11. Get 'name' property from path.
                            12. Check for any modelled 'sfs-cache'
                                        items under the sfs-pool path.
                            For each path of type 'sfs-cache':
                                13. Get 'name' property from path.
                                14. Check for any modelled 'sfs-filesystem'
                                            items under the sfs-pool path.
                                For each path of type 'sfs-filesystem':
                                    15. Get 'path' and 'size' properties.
                                    16. Ensure file path specified in model
                                            exists on SFS node and matches
                                                size defined.
                                    17. Check for any modelled 'sfs-export'
                                            items under the sfs-pool path.
                                    18. Match SFS file path, IPs and user
                                            options on model with SFS.
        """
        for node in self.all_nodes:
            node_name = node["name"]

            # 1. Check for any modelled 'nfs-mount' items on node
            nfs_mount_paths = self.find(self.ms_node, node["url"],
                                "nfs-mount", assert_not_empty=False)

            # For each path of type 'nfs-mount':
            for mount_path in nfs_mount_paths:
                # 2. Get the properties of the path
                prop_nfs = self.get_props_from_url(self.ms_node, mount_path)

                export_path = prop_nfs['export_path']
                mnt_point = prop_nfs['mount_point']
                mount_options = prop_nfs['mount_options']
                provider = prop_nfs['provider']

                # 3. Check for any modelled 'nfs-service' items
                nfs_serv = self.find(self.ms_node, "/infrastructure",
                            "nfs-service", assert_not_empty=False)

                # 4. Check for any modelled 'sfs-service' items
                sfs_services = self.find(self.ms_node, "/infrastructure",
                                     "sfs-service", assert_not_empty=False)

                # 5. Check for any modelled 'sfs-virtual-server' items
                sfs_virt = self.find(self.ms_node, "/infrastructure",
                            "sfs-virtual-server", assert_not_empty=False)

                # 6. Run 'mount' command on node to compare 'nfs-mount'
                # properties and 'ipv4address' property from any nfs-service,
                # sfs-service and sfs-virtual-server paths found
                self._mount_checks(nfs_serv, sfs_services, sfs_virt, provider,
                            export_path, node_name, mnt_point, mount_options)

                # For each path of type 'sfs-virtual-server':
                for virt_path in sfs_virt:
                    # 7. Get the properties of the path
                    prop_sfs_virt = self.get_props_from_url(
                        self.ms_node, virt_path)

                    # 8. If sfs-virtual-server 'name' property matches
                    #       nfs-mount 'provider' property, update connection
                    #           data of SFS node
                    if prop_sfs_virt['name'] == provider:
                        # Get an SFS server by its vip1 address
                        sfs_node = self.get_sfs_node_from_vip1(
                            prop_sfs_virt['ipv4address'])

                        self.set_node_connection_data(sfs_node,
                          username=test_constants.SFS_MASTER_USR,
                          password=test_constants.SFS_MASTER_PW)

                    # For each path of type 'sfs-service':
                    for sfs_serv_path in sfs_services:
                        # If the 'sfs-service' item parents the
                        #       'sfs-virtual-server' being tested:
                        if sfs_serv_path in virt_path:
                            # 9. Test sfs-service 'user_name' property
                            self._sfs_services(sfs_serv_path)

                            # 10. Check for any modelled 'sfs-pool'
                            #       items under the sfs-service path
                            sfs_pool = self.find(self.ms_node, sfs_serv_path,
                                            "sfs-pool", assert_not_empty=False)

                            # For each path of type 'sfs-pool':
                            for pool_path in sfs_pool:
                                # 11. Get 'name' property from path
                                pool_name = self.get_props_from_url(
                                    self.ms_node, pool_path)['name']

                                # 12. Check for any modelled 'sfs-cache' items
                                #           under the sfs-pool path
                                sfs_cache = self.find(self.ms_node, pool_path,
                                        "sfs-cache", assert_not_empty=False)

                                # For each path of type 'sfs-cache':
                                for cache_path in sfs_cache:
                                    # 13. Get 'name' property from path
                                    cache_name = self.get_props_from_url(
                                        self.ms_node, cache_path)['name']

                                    # 14. Check for any modelled sfs-filesystem
                                    #       items under the sfs-pool path
                                    sfs_fs = self.find(self.ms_node,
                                        pool_path, "sfs-filesystem",
                                            assert_not_empty=False)

                                    # For each path of type 'sfs-filesystem':
                                    for file_path in sfs_fs:
                                        # 15. Get 'path' and 'size' properties
                                        fs_prop = self.get_props_from_url(
                                            self.ms_node, file_path)
                                        fs_path = fs_prop['path']
                                        fs_size = fs_prop['size']

                                        if fs_path == export_path:
                                            # 16. Ensure file path specified in
                                            #   model exists on SFS node
                                            #       and matches size defined.
                                            self._sfs_filesystem(fs_size,
                                                fs_path, sfs_node, pool_name,
                                                node_name, mnt_point, fs_prop,
                                                sfs_cache, cache_name)

                                        # 17. Check for any modelled
                                        #   'sfs-export' items under
                                        #       the sfs-pool path
                                        sfs_exports = self.find(self.ms_node,
                                            file_path, "sfs-export",
                                                assert_not_empty=False)

                                        # For each path of type 'sfs-export':
                                        for sfs_export in sfs_exports:
                                            # 18. Match SFS file path, IPs and
                                            # user options on model with SFS
                                            self._sfs_export(sfs_export,
                                                             sfs_node, fs_path)
