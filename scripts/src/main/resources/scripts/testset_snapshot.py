"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     July 2015
@author:    Brian Carey
"""

from litp_generic_test import GenericTest, attr, StorageUtils
import test_constants
import sys


class Snapshot(GenericTest):
    """Test the 'snapshot' LITP item type."""

    def setUp(self):
        """
        Description:
            Runs before every single test
        Results:
            The super class prints out diagnostics and variables
            common to all tests available
        """

        super(Snapshot, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Perform Test Cleanup
        Results:
            Items used in the test are cleaned up and the
            super class prints out end test diagnostics
        """
        super(Snapshot, self).tearDown()

    def _get_all_volumes(self, url, driver):
        """
        Get all the file systems as a list of dictionaries.
        It combines the properties from the item types storage-profile,
        volume-group and file-system.
        """
        file_systems = []
        vold = {}
        # Get all storage_profiles paths
        sps = self.find(self.ms_node, url, 'storage-profile',
                        assert_not_empty=False)
        if not sps:
            self.log("info", "No storage profile in model")

        self.log("info", "SPs are {0}".format(str(sps)))

        # For each storage_profile path.
        for stor_prof in sps:
            # Get the storage profile name.
            vold["storage_profile"] = stor_prof.split("/")[-1]

            # Get the volume_driver type
            sp_props = self.get_props_from_url(self.ms_node, stor_prof)
            vold["volume_driver"] = sp_props["volume_driver"]

            # If incorrect volume driver found continue onto next storage
            #  profile
            if vold["volume_driver"] != driver:

                self.log("info", "Incorrect volume driver")

                self.log("info", "Expected volume driver: {0}"
                         .format(driver))

                self.log("info", "Actual volume driver: {0}".format(
                    vold["volume_driver"]))

                continue

            # Get volume group paths
            vgs = self.find(self.ms_node, stor_prof, 'volume-group')
            self.log("info", "VGs in {0} are {1}"
                     .format(vold["storage_profile"], str(vgs)))

            # For all volume groups
            for vg_path in vgs:
                # Get volume_group name
                vg_props = self.get_props_from_url(self.ms_node, vg_path)
                vold["volume_group_name"] = vg_props["volume_group_name"]

                # Get the volume paths
                vols = self.find(self.ms_node, vg_path, 'file-system')
                self.log("info", "Vols in {0} are {1}"
                         .format(vold["volume_group_name"], str(vols)))

                # For each volume create a dictionary of attributes
                for vol in vols:

                    # volume_name_part1 and volume_name_part2 are used to
                    # create the full volume name from the URL
                    vold['volume_name_part2'] = vol.split("/")[-1]
                    vold['volume_name_part1'] = vol.split("/")[-3]
                    vol_props = self.get_props_from_url(self.ms_node, vol)
                    vold['snap_size'] = vol_props["snap_size"]
                     #LITPCDS-12270, Mount point is optional
                    if 'mount_point' in vol_props.keys():
                        vold['mount_point'] = vol_props["mount_point"]
                    else:
                        vold['mount_point'] = None
                    vold['type'] = vol_props["type"]
                    vold['size'] = vol_props["size"]
                    if "snap_external" in vol_props:
                        vold['snap_external'] = vol_props["snap_external"]

                    # Copy volume dictionary to the list.
                    file_systems.append(vold.copy())

        return file_systems

    def _check_vxvm_snapshot(self, name, vxvol, cluster):
        """
        Carries out checks to see if VxVM snapshots exist and if their
        properties match what is in the LITP model
        """

        counter = 0

        # Check if snap_size property is present
        if "snap_size" in vxvol and vxvol["snap_size"] != "0":
            # Create string of expected VxVM snapshot
            expect = "L_" + vxvol["volume_name_part2"] + name

            for node in cluster["nodes"]:

                self.log("info", "Checking if VxVM snapshot '{0}' has been "
                                 "created on {1}".format(expect, node["name"]))

                # Check if expected snapshot is created
                cmd = test_constants.VXSNAP_PATH + " -g {0} list | grep {1}"\
                    .format(vxvol["volume_group_name"], expect)

                stdout, stderr, rc = self.run_command(node["name"], cmd,
                                                      su_root=True)

                self.assertEqual([], stderr)
                self.assertNotEqual([], rc)

                # In the case that the VxVM volume is not on the node
                if expect not in stdout[0]:
                    self.log("info", "VxVM snapshot '{0}' not on {1}"
                             .format(expect, node["name"]))
                    continue

                self.log("info", "VxVM snapshot '{0}' is on {1}"
                         .format(expect, node["name"]))

                counter += 1

            if vxvol["snap_size"] == "0":
                self.log("info", "snap_size = 0 - checking that snapshot '{0}'"
                                 " has not been created".format(expect))
                self.assertEqual(0, counter)

            else:
                self.log("info", "Checking that snapshot '{0}' has been "
                                 "created on only one node in cluster"
                         .format(expect))
                self.assertEqual(1, counter)

    def _check_lvm_snap_size(self, volsize, snap_size, node, expect):
        """
        This checks that snap_size property from the model has been applied
        correctly to the LVM snapshots
        """

        if len(volsize) > 4:

            volsize = str(float(volsize[:-1]) / 1000) + "G"

        # This creates a string of the expected snapshot size from both the
        # volume size and snap_size properties in model
        snapshot_size = str((float(volsize[:-1]) * int(snap_size)) / 100) + "G"

        # Look for the expected snapshot name in the 'lsblk' output in
        # order to get the actual snapshot size
        cmd = "/bin/lsblk -r | grep {0}-cow".format(expect)

        stdout, stderr, rc = self.run_command(node["name"], cmd, su_root=True)

        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, rc)

        new_stdout = stdout[0].split()

        if "." not in new_stdout[3]:
            snapshot_size = snapshot_size.split(".")[0] + "G"

        # If actual snapshot size is in MB:
        if "M" in new_stdout[3]:

            if "M" in volsize:
                vol_size_mb = volsize[:-1]

            else:
                # Convert the volume size to MB
                vol_size_mb = StorageUtils().convert_gb_to_mb(volsize)

            # Calculate the expected snapshot size in MB
            snapshot_size = ((float(vol_size_mb) * float(snap_size)) / 100)

            # If remainder, round up to nearest MB
            if snapshot_size % 1 != 0:
                snapshot_size = (int(snapshot_size) + 1)

            else:
                snapshot_size = (int(snapshot_size))

            # LVM snapshot size has to be rounded up to nearest 4MB
            if snapshot_size % 4 != 0:
                snapshot_size = (((int(snapshot_size / 4)) + 1) * 4)

            # Create string for comparison
            snapshot_size = str(snapshot_size) + "M"

        self.log("info", "Checking that 'snap_size' has been applied "
                         "correctly")

        self.log("info", "Checking that {0} is in {1}"
                 .format(snapshot_size, new_stdout))

        # Compare the expected snapshot size to the actual snapshot size
        self.assertTrue(snapshot_size in new_stdout[3])

    def _check_lvm_snapshot(self, node, name):
        """
        Gets all lvm volumes from the model and checks if the correct
        snapshots have been created
        """

        # Get all volumes under each node
        fss = self._get_all_volumes(node["url"], "lvm")

        # For each volume:
        for filesys in fss:

            # Get path to snapshot directory
            path = "/dev/" + filesys["volume_group_name"]

            # Get list of snapshot directory contents
            dir_list = self.list_dir_contents(node["name"], path)

            snap_size = filesys["snap_size"]

            # Creates string of volume name from the URL which is
            # used to complete the expected name of the snapshot
            vols = (filesys["volume_name_part1"] + "_" +
                    filesys["volume_name_part2"])

            # Skip SWAP volumes
            if "swap" in vols:
                continue

            self.log("info", "List in snapshot directory: {0}"
                     .format(dir_list))

            # Create the string of the expected snapshot name
            expect = "L_" + vols + name

            # Check if the 'snap_size' is set to 0
            if snap_size == "0":

                self.log("info", "snap_size = 0 for volume: {0}"
                         .format(vols))

                self.log("info", "Checking that Snapshot '{0}'"
                                 " is not created".format(expect))

                # 1. If set to 0 check that snapshot is not
                #  created
                self.assertFalse(any(
                    expect in x for x in dir_list))
                continue

            if "snap_external" in filesys:
                if filesys["snap_external"] == "true":
                    self.log("info", "External snapshot")
                    continue

            self.log("info", "Checking that {0} is in snapshot "
                             "directory".format(expect))

            # Check that snapshots are present in the snapshot
            #  directory
            self.assertTrue(expect in dir_list)

            # Check that the snap_size property has been
            # applied correctly
            self.log("info", "Beginning LVM snap_size checks")

            self._check_lvm_snap_size(filesys["size"], snap_size,
                                      node, expect)

    def _get_sfs_details_from_virt_server(self, vs_url, vserver):
        """
        Find the sfs node for the virtual server url and properties passed.
        """

        try:
            sfs_nodes = self.get_sfs_node_from_ipv4(vserver["ipv4address"])
            return sfs_nodes[0]
        except AssertionError:
            self.log("info", "No SFS node found with IPv4 address:"
                             " {0}".format(vserver["ipv4address"]))

        parent = self.find_parent_path_from_item_type(self.ms_node,
                                                      "sfs-service",
                                                      vs_url)
        sfs_ips = [self.get_props_from_url(self.ms_node, parent,
                                       filter_prop="management_ipv4")]
        # Get all virt servers under this sfs-service
        virt_servers = self.find(self.ms_node, parent, "sfs-virtual-server")

        for vir_ser in virt_servers:
            sfs_ips.append(self.get_props_from_url(self.ms_node, vir_ser,
                                    filter_prop="ipv4address"))

        for ip_addr in sfs_ips:
            try:
                sfs_nodes = self.get_sfs_node_from_ipv4(ip_addr)
                return sfs_nodes[0]
            except AssertionError:
                continue
        print "ERROR: Cannot find SFS node for any of the sfs-virtual-server "\
              "items or parent sfs-service: {0}".format(vs_url)
        sys.exit(1)

    def _check_sfs_snapshot(self, name, node):
        """
        Checks if SFS within deployment and if present then checks SFS
        snapshots. Returns True if SFS snapshots created correctly or if
        no SFS within deployment.
        """

        self.log("info", "Checking if SFS in model")

        mount_providers = []
        # Find mounts under each node
        mount_urls = self.find(self.ms_node, node["url"],
                               "reference-to-nfs-mount",
                               assert_not_empty=False)

        for mount in mount_urls:

            # Get properties of each mount
            props = self.get_props_from_url(self.ms_node, mount)

            mount_provider = props["provider"]

            # If mount provider already in list - do not include it
            if mount_provider not in mount_providers:

                mount_providers.append(mount_provider)

        # Get sfs-virtual-server item types from model
        virt_server_urls = self.find(self.ms_node,
                                     "/infrastructure/",
                                     "sfs-virtual-server",
                                     assert_not_empty=False)

        for virt_server in virt_server_urls:

            # Get properties for each one
            props = self.get_props_from_url(self.ms_node, virt_server)

            # If the sfs-virtual-server is a mount point provider,
            #  start SFS checks
            for mount_provider in mount_providers:

                if mount_provider == props["name"]:

                    sfs_node = \
                        self._get_sfs_details_from_virt_server(virt_server,
                                                               props)

                    # Set the connection details for SFS node
                    self.set_node_connection_data(
                        sfs_node, username=test_constants.SFS_MASTER_USR,
                        password=test_constants.SFS_MASTER_PW)

                    self.log("info", "Mount provider '{0}' is equal"
                                     " to sfs-virtual server name '{1}'"
                             .format(mount_provider,
                                     props["name"]))

                    url_parts = virt_server.split("/")

                    url = "/" + "/".join(url_parts[1:-2])

                    self.log("info", "Looking for SFS-filesystems under "
                                     "corresponding URL '{0}'".format(url))

                    # Find the SFS URLs in the LITP model
                    sfs_urls = self.find(self.ms_node, url, "sfs-filesystem",
                                         assert_not_empty=False)

                    # For each SFS in the model:
                    for sfs_url in sfs_urls:

                        # Get SFS properties from the model
                        sfs_props = self.get_props_from_url(
                            self.ms_node, sfs_url)

                        # Get the SFS name from the path
                        sfs_name = sfs_props["path"].split("/vx/")[1]

                        if "snap_size" in sfs_props:
                            # Check if the snap size is 0.
                            if sfs_props["snap_size"] == "0":
                                self.log("info", "snap_size is 0, no snapshot"
                                                 " expected.")
                                continue

                        if "cache_name" in sfs_props:
                            # Needed to ensure the expected snapshot
                            # string is correct
                            if name == "_":
                                name = "__"

                            # Create string of expected snapshot name
                            expect = "L_" + sfs_name + name[:-1]

                            self.log("info", "Expected snapshot name: "
                                             "'{0}'".format(expect))

                            self.log("info", "Checking that '{0}' has "
                                             "been created"
                                     .format(expect))

                            # Check for expected snapshot
                            self.log("info", "Checking that SFS "
                                             "snapshot '{0}' is "
                                             "present".format(expect))

                            self.assertTrue(
                                self.is_sfs_snapshot_present(sfs_node,
                                                             expect))

                    self._check_sfs_snap_size(sfs_urls, sfs_node)

    def _check_sfs_snap_size(self, sfs_urls, sfs_node):
        """
        Checks that the snap_size property has been applied correctly to the
        SFS snapshot
        """

        total_expect_size = 0
        cname = ""

        # For each SFS in the model:
        for sfs_url in sfs_urls:

            # Get SFS properties from the model
            sfs_props = self.get_props_from_url(self.ms_node, sfs_url)

            # Check if cache_name is in SFS properties
            if "cache_name" in sfs_props:

                size = int(sfs_props["size"][:-1])

                # If in Gb convert to Mb
                if "G" in sfs_props["size"]:
                    size = StorageUtils().convert_gb_to_mb(
                        sfs_props["size"])
                    size = float(size)

                snap_size = float(sfs_props["snap_size"]) / 100

                # Expected size of snapshot
                expect_size = float(size * snap_size)

                total_expect_size += expect_size

                # Round expected size
                total_expect_size = (round(total_expect_size))

                total_expect_size = int(total_expect_size)

                cname = sfs_props["cache_name"]

        sfs_caches = self.get_sfs_cache_list(sfs_node)

        for cache in sfs_caches:

            # Check that 'snap_size' has been
            # applied correctly
            if cname == cache["NAME"]:
                self.log("info", "Checking snap_size set correctly")
                self.log("info", "Checking calculated cache size: {0} is equal"
                                 " to the cache size on the SFS: {1}"
                         .format(cache["TOTAL"], total_expect_size))

                self.assertEqual(int(cache["TOTAL"]), total_expect_size)

    @attr('all', 'revert', 'system_check', 'snapshot', 'snapshot_tc01')
    def test_01_p_snapshot(self):
        """
        Description:
            Test the 'snapshot-base' LITP item type

        Actions:
            1. Find any 'snapshot-base' items in the model
            2. Create a list of all nodes in the cluster including the MS
            3. For each snapshot:
                a. Get the name of the snapshot from the URL
                b. Get the properties of the snapshot
                c. Get the state of the snapshot
                d. Check that the snapshot is in 'Applied' state
                e. Check that the 'active' property is present
            4. For each node in cluster:
                a. Check for LVM snapshots
                b. Check for SFS snapshots
            5. Get all VxVM volumes that are present in the LITP model
            6. For each VxVM volume in model:
                a. Carry out checks for VxVM snapshots

        Result:
            Returns True if all snapshots have been created correctly or
            if there is no snapshot item in the model
        """

        # 1. Find any 'snapshot-base' items in the model
        snapshots = self.find(self.ms_node, "/snapshots/", "snapshot-base",
                              assert_not_empty=False)

        # If no snapshots in model, test passes
        if not snapshots:
            self.log("info", "No snapshot in model")

        for cluster in self.model["clusters"]:

            # 2. Create a list of all nodes in the cluster including the MS
            all_nodes = cluster["nodes"][:]
            all_nodes.extend(self.model["ms"][:])

            # 3. For each snapshot:
            for snapshot in snapshots:

                # a. Get the name of the snapshot from the URL
                name = "_" + snapshot.split("/snapshots/")[-1] + "_"

                # Used to create the string of the expected name
                # of the snapshot eg. when a named snapshot 'test' is created
                # the name is 'litp_filesysname_test_snapshot', the
                # corresponding deployment snapshot name would be
                # 'litp_filesysname_snapshot'
                if name == "_snapshot_":
                    name = "_"

                self.log("info", "Printing URL of snapshot: {0}"
                         .format(snapshot))

                # b. Get the properties of the snapshot
                props = self.get_props_from_url(self.ms_node, snapshot)

                self.log("info", "Printing snapshot properties:{0}"
                         .format(props))

                # c. Get the state of the snapshot
                state = self.get_item_state(self.ms_node, snapshot)

                self.log("info", "State of snapshot in model: {0}"
                         .format(state))

                self.log("info",
                         "Check that the snapshot is in 'Applied' state")

                # d. Check that the snapshot is in an 'Applied' state
                self.assertTrue(state == "Applied")

                # e. Check that the property 'active' is present
                self.log("info", "Checking if 'active' property is present")
                self.assertTrue("active" in props)

                # 4. For each node in cluster:
                for node in all_nodes:

                    # a. Check for LVM snapshots
                    self._check_lvm_snapshot(node, name)

                    # b. Check for SFS snapshots
                    self.log("info", "Check for SFS snapshots")
                    self._check_sfs_snapshot(name, node)

                # 5. Get all VxVM volumes that are present in the LITP model
                vxvm = self._get_all_volumes(cluster["url"] +
                                             "/storage_profile", "vxvm")

                if not vxvm:
                    self.log("info", "No VxVM volumes found in model")
                    continue

                # 6. For each VxVM volume in model:
                for vxvol in vxvm:

                    # If snap_external is true - skip check
                    if "snap_external" in vxvol:
                        if vxvol["snap_external"] == "true":
                            continue

                    # a. Carry out checks for VxVM snapshots
                    self.log("info", "Checking for VxVM snapshots for '{0}'"
                             .format(vxvol["volume_group_name"]))
                    self._check_vxvm_snapshot(name, vxvol, cluster)
