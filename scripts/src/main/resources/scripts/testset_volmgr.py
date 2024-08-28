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

from litp_generic_test import GenericTest, attr
import test_constants


class Volmgr(GenericTest):
    """Test the volmgr item types"""

    def setUp(self):
        """
        Description:
            Runs before every single test
        Results:
            The super class prints out diagnostics and variables
            common to all tests available
        """

        super(Volmgr, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]

        self.all_clusters = self.model["clusters"]

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
        super(Volmgr, self).tearDown()

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
                    #LITPCDS-12270, Mount point is optionally
                    if 'mount_point' in vol_props.keys():
                        vold['mount_point'] = vol_props["mount_point"]
                    else:
                        vold['mount_point'] = None

                    vold['type'] = vol_props["type"]
                    vold['size'] = vol_props["size"]

                    # Copy volume dictionary to the list.
                    file_systems.append(vold.copy())

        return file_systems

    def _check_mount_point(self, node, mount, vol):
        """
        Carries out checks on the mount point property of volumes.
        Returns True if mount points are applied correctly.
        """
        if mount == "swap":
            mount = "[SWAP]"

        # i. Grep the lvscan to confirm vol is present
        cmd = "/sbin/lvscan | grep {0}".format(vol)
        stdout, stderr, rc = self.run_command(node["name"], cmd, su_root=True)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, rc)

        # j. Grep mount command to ensure only volume with mount_point declared
        # are mounted and that mount point is correct.
        self.log("info", "Checking that the correct mount point "
                         "has been applied")

        cmd = "/bin/mount | grep {0}".format(vol)
        stdout, stderr, rc = self.run_command(node["name"], cmd)

        #LITPCDS-12270, Mount point is optional
        if mount is None:
            self.assertEqual([], stdout)
        else:
            self.assertTrue(mount in item for item in stdout)

        return True

    def _check_vxvm(self, node, vol):
        """
        This method is used to check properties of VxVM volumes on managed
        nodes. It returns True if the volumes have been set up correctly
        according to what is in the LITP model.
        """

        # Changes size parameter for vxprint command
        vsize = "g"

        if "M" in vol["size"]:
            vsize = "m"

        elif "T" in vol["size"]:
            vsize = "t"

        cmd = "/sbin/vxprint -g {0} -u{1} | grep 'pl *.*{2}-'".format(
            vol["volume_group_name"], vsize, vol["volume_name_part2"])

        stdout, stderr, rc = self.run_command(node["name"], cmd,
                                              su_root=True)

        # Check that the volume name has been applied
        #  correctly
        self.log("info", "Checking volume_name applied "
                         "correctly")
        self.log("info", "Checking that '{0}' is in {1}"
                 .format(vol["volume_name_part2"], stdout))
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, rc)

        for line in stdout:
            # splits output into a usable list
            split_stdout = line.split()

            # Check that the volume size is applied
            #  correctly
            self.log("info", "Checking that volume size applied "
                             "correctly")
            self.log("info", "Checking that '{0}{1}' is in {2}"
                     .format(vol["size"][:-1], vsize, stdout))
            self.assertEqual(vol["size"][:-1], split_stdout[4][:-4])

        # Confirm LITP model has correct volume_driver
        self.log("info", "Checking that volume_driver is "
                         "vxvm")
        self.assertEqual("vxvm", vol["volume_driver"])

        # Confirm LITP model has correct volume type
        self.log("info", "Checking that type is "
                         "'vxfs'")
        self.assertEqual("vxfs", vol["type"])

        self.log("info", "VxVM check complete on {0}".format(node["name"]))

        return True

    @attr('all', 'revert', 'system_check', 'volmgr', 'volmgr_tc01')
    def test_01_p_volmgr(self):
        """
        Description:
            Test the volmgr item types and their properties in the model
            have been applied correctly on the managed nodes.

        Actions:
            1. Get all volumes from the LITP model for each node
            2. Get URLs of all physical devices in the LITP model
            3. For each physical device in the model:
                1. Check that 'device name' is not empty
            4. For each volume in the model:
                a. Create a string of the volume name from the URL
                b. Check that the properties which are 'always present'
                    are present
                c. Check that 'volume driver' is "lvm"
                d. Run 'blkid' command in order to check that the volume type
                    in the model has been applied correctly
                e. Check that the volume type has been correctly applied
                f. Run 'lsblk -r' command in order to get the volume size and
                    driver
                g. Check that the volume size and volume driver are equal to
                    that in the model
                h. Check the mount point of the volume
                i. Check that 'volume group name' from model has been applied
            5. Get all vxvm volumes from the LITP model for each cluster
            6. For each vxvm volume:
                a. For each node in cluster:
                    1. Check if VxVM volume is on the node
                    2. If none, move onto next node.
                    3. Counter increases when VxVm volume found on a node
                    4. Carry out VxVm checks
                b. Ensure that the vxvm volume is on just one of the
                    cluster nodes
        Result:
            Returns True if volumes have been configured correctly
            when compared to the LITP model
        """

        for cluster in self.model["clusters"]:

            all_nodes = cluster["nodes"][:]
            all_nodes.extend(self.model["ms"][:])

            for node in all_nodes:

                # 1. Get all volumes from the LITP model for each node
                fss = self._get_all_volumes(node["url"], "lvm")

                # 2. Get URLs of all physical devices in the LITP model
                p_devices = self.find(self.ms_node, node["url"],
                                      "physical-device",
                                      assert_not_empty=False)

                self.log("info", "List of 'physical-device' item types "
                                 "in model for {0}: {1}".format(node["name"],
                                                                p_devices))

                # 3. For each physical device in the model:
                for device in p_devices:

                    device_props = self.get_props_from_url(self.ms_node,
                                                           device)
                    device_name = device_props["device_name"]

                    # a. Check that 'device name' is not empty
                    self.log("info", "Checking that 'device_name' is not"
                                     " empty")

                    self.assertTrue(device_name != "")

                    self.log("info", "Device Name: {0}".format(
                        device_name))

                # 4. For each volume in the model:
                for filesys in fss:

                    self.log("info", "{0}".format(filesys))

                    size = filesys["size"]

                    # a. Create a string of the volume name from the URL
                    vol = filesys['volume_name_part1'] + "_" +\
                        filesys['volume_name_part2']

                    # c. Check that 'volume driver' is "lvm"
                    self.log("info", "Checking that 'volume driver' is 'lvm'")

                    self.log("info", "'volume_driver' is {0}"
                             .format(filesys["volume_driver"]))

                    self.assertTrue(filesys["volume_driver"] == "lvm")

                    self.log("info", "Node - {0}".format(node["name"]))

                    # d. Run 'blkid' command in order to check that the volume
                    #  type in the model has been applied correctly
                    cmd = "/sbin/blkid | grep {0}".format(vol)
                    stdout, stderr, rc = self.run_command(node["name"], cmd,
                                                          su_root=True)
                    self.assertEqual([], stderr)
                    self.log("info", "Check if '{0}' is in BLKID output"
                             .format(filesys["type"]))

                    # e. Check that the volume type has been correctly applied
                    self.log("info", "Checking if volume type is equal to that"
                                     " in the model")
                    self.assertTrue(self.is_text_in_list(filesys["type"],
                                                         stdout))

                    # f. Run 'lsblk -r' command in order to get the volume size
                    #  and driver
                    cmd = "/bin/lsblk -br | grep '{0} '".format(vol)
                    stdout, stderr, rc = self.run_command(node["name"], cmd)
                    self.assertNotEqual([], stdout)
                    self.assertEqual([], stderr)
                    self.assertEqual(0, rc)
                    lsblk = stdout

                    for line in lsblk:

                        # Splits up the strings in the list and removes
                        # white spaces
                        new_stdout = line.split()

                        if "M" in size:
                            size = str(int(size[:-1]) * 1048576)
                        if "G" in size:
                            size = str(int(size[:-1]) * 1073741824)

                        # g. Check that the volume size and volume driver
                        # are equal to that in the model
                        self.log("info", "'{0}' in {1}".format(
                            vol, new_stdout[0]))
                        self.log("info", "Checking if volume size is equal"
                                         " to that in the model")

                        self.log("info", "Checking if {0} is equal to {1}"
                                 .format(size, new_stdout[3]))

                        self.assertEqual(size, new_stdout[3])

                        self.log("info", "Checking that volume driver is "
                                         "correctly applied")

                        self.log("info", "Checking if {0} is equal to {1}"
                                 .format(filesys["volume_driver"],
                                         new_stdout[5]))

                        self.assertEqual(filesys["volume_driver"],
                                         new_stdout[5])

                    # h. Check the mount point of the volume
                    if 'mount_point' in filesys:
                        mount = filesys["mount_point"]
                        self.log("info",
                                 "Checking mount point of {0}".format(vol))
                        self.assertTrue(self._check_mount_point(node,
                                                                mount,
                                                                vol))

                    self.log("info", "Checking volume_group_name")

                    vgdisplay = self.get_vg_info_on_node(node["name"])

                    # i. Check that 'volume group name' from model has been
                    # applied
                    self.log("info", "Checking '{0}' is in {1}"
                             .format(filesys["volume_group_name"], vgdisplay))

                    self.assertTrue(
                        filesys["volume_group_name"] in vgdisplay)

            # 5. Get all vxvm volumes from the LITP model for
            #  each cluster
            vxvm = self._get_all_volumes(cluster["url"] + "/storage_profile",
                                         "vxvm")

            if not vxvm:
                self.log("info", "No VxVM volumes found in model")
                continue

            # 6. For each vxvm volume
            for vol in vxvm:

                # Counter to ensure that each volume only appears on one
                # node in the cluster
                counter = 0

                self.log("info", "Volume : {0}".format(vol))

                # a. For each node in cluster:
                for node in cluster["nodes"]:

                    self.log("info", "Checking volume_group_name applied "
                                     "correctly")

                    self.log("info", "Checking if '{0}' is on {1}"
                             .format(vol["volume_group_name"], node["name"]))

                    # 1. Check if VxVM volume is on the node
                    cmd = test_constants.VXDG_PATH + " list | grep {0}"\
                        .format(vol["volume_group_name"])

                    stdout, stderr, rc = self.run_command(node["name"],
                                                          cmd,
                                                          su_root=True)
                    self.assertEqual([], stderr)

                    # 2. If none, move onto next node.
                    if stdout == []:
                        self.log("info", "Volume group '{0}' is not {1}"
                                 .format(vol["volume_group_name"],
                                         node["name"]))
                        continue

                    self.log("info", "Volume group {0} is on {1}"
                             .format(vol["volume_group_name"], node["name"]))

                    # 3. Counter increases when VxVm volume found on a node
                    counter += 1

                    # 4. Carry out VxVm checks
                    self.log("info", "Starting VxVM check for {0}"
                             .format(node["name"]))

                    self.assertTrue(self._check_vxvm(node, vol))

                # b. Ensures that the vxvm volume is on just one of the
                # cluster nodes
                self.log("info", "Checking that volume is present on only one "
                                 "node in the cluster")
                self.assertEqual(1, counter)
