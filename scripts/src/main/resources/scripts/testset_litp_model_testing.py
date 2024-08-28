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
import test_constants


class LitpModelTests(GenericTest):
    """
    Tests creating and removing Deployment and Named Snapshots
            with the create_snapshot and remove_snapshot commands.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(LitpModelTests, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]

    def tearDown(self):
        """ Teardown run after every test """

        super(LitpModelTests, self).tearDown()

    def _get_list_all_snapshots_on_model(self):
        """
        Description:
            Get a list of all snapshots under the /snapshots path.
         """
        snapshot_urls = self.find(self.ms_node, "/snapshots",
                              "snapshot-base", assert_not_empty=False)
        return snapshot_urls

    def _remove_all_snapshots(self):
        """
        Description:
            Remove all snapshots found in LITP model using CLI command.
         """
        snapshot_urls = self._get_list_all_snapshots_on_model()
        for snapshot_url in snapshot_urls:
            snapshot_name = snapshot_url.split('/')[-1]

            if snapshot_name == 'snapshot':
                # This is the deployment snapshot.
                self.execute_cli_removesnapshot_cmd(self.ms_node)
            else:
                # This is the named snapshot.
                args = "-n {0}".format(snapshot_name)
                self.execute_cli_removesnapshot_cmd(self.ms_node, args)

            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                test_constants.PLAN_COMPLETE))

    @attr('all', 'revert', 'system_functionality', 'LitpModelTests',
          'LitpModelTests_tc01')
    def test_create_litp_snapshot(self):
        """
        Description:
            Create a deployment snapshot, but not clean it up.
        Actions:
            1. Check for any existing snapshots and remove them.
            2. Run the create_snapshot command.
            3. Assert that there are no errors.
            4. Wait for the plan to finish.
        """
        # 1. Check for any existing snapshots and remove them
        self._remove_all_snapshots()

        # 2. Run the create_snapshot command
        create_snapshot_cmd = self.cli.get_create_snapshot_cmd()
        self.run_command(self.ms_node,
                        create_snapshot_cmd, add_to_cleanup=False)

        # 3. Assert that there are no errors
        stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, rc)

        # 4. Wait for the plan to finish
        self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                                 test_constants.PLAN_COMPLETE))

    @attr('all', 'revert', 'system_functionality', 'LitpModelTests',
          'LitpModelTests_tc02')
    def test_remove_litp_snapshot(self):
        """
        Description:
            Remove a deployment snapshot, assuming it exists.
        Actions:
            1. Run the remove_snapshot command.
            2. Assert that there are no errors.
            3. Wait for the plan to finish.
        """
        # 1. Run the remove_snapshot command
        remove_snapshot_cmd = self.cli.get_remove_snapshot_cmd()
        self.run_command(self.ms_node,
                            remove_snapshot_cmd, add_to_cleanup=False)

        # 2. Assert that there are no errors
        stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, rc)

        # 3. Wait for the plan to finish
        self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE))

    @attr('all', 'revert', 'system_functionality', 'LitpModelTests',
          'LitpModelTests_tc03')
    def test_create_litp_named_snapshot(self):
        """
        Description:
            Create a named snapshot with name 'cisnap', but not clean it up.
        Actions:
            1. Run the create_snapshot command with the
                            'name' property given as an argument.
            2. Assert that there are no errors.
            3. Wait for the plan to finish.
        """
        # Check for any existing snapshots and remove them
        # self._remove_all_snapshots()

        args = '-n cisnap'
        # 1. Run the create_snapshot command with the
        #           'name' property given as an argument
        create_snapshot_cmd = self.cli.get_create_snapshot_cmd(args)
        self.run_command(self.ms_node,
                        create_snapshot_cmd, add_to_cleanup=False)

        # 2. Assert that there are no errors
        stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, rc)

        # 3. Wait for the plan to finish
        self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE))

    @attr('all', 'revert', 'system_functionality', 'LitpModelTests',
          'LitpModelTests_tc04')
    def test_remove_litp_named_snapshot(self):
        """
        Description:
            Remove a named snapshot with name 'cisnap', assuming it exists.
        Actions:
            1. Run the remove_snapshot command with the
                            'name' property given as an argument.
            2. Assert that there are no errors.
            3. Wait for the plan to finish.
        """
        args = '-n cisnap'
        # 1. Run the remove_snapshot command with the
        #                       'name' property given as an argument.
        remove_snapshot_cmd = self.cli.get_remove_snapshot_cmd(args)
        self.run_command(self.ms_node,
                            remove_snapshot_cmd, add_to_cleanup=False)

        # 2. Assert that there are no errors
        stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, rc)

        # 3. Wait for the plan to finish
        self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE))

    @attr('all', 'revert', 'system_functionality', 'LitpModelTests',
          'LitpModelTests_tc05', 'physical')
    def test_litp_depl_and_named_snapshot(self):
        """
        Description:
            Create a deployment snapshot and named snapshot with name 'cisnap'.
            Remove both snapshots.
        Actions:
            1. Check all modelled 'file-system' items on MS.
            2. Get the item with path '.../root'.
            3. Get the 'snap_size' property's value to ensure it is not 0.
            If 'snap_size' is not 0:
            4. Check for any existing snapshots and remove them.
            5. Change 'snap_size' value to ensure 2 snapshots will fit on disk.
                a. Store properties of path for restoration at the end of test.
                b. Update the 'snap_size' property to 30.
            6. Create a deployment snapshot.
                a. Run the create_snapshot command.
                b. Assert that there are no errors.
                c. Wait for the plan to finish.
            7. Create a named snapshot.
                a. Run the create_snapshot command with the
                            'name' property given as an argument.
                b. Assert that there are no errors.
                c. Wait for the plan to finish.
            8. Remove the deployment snapshot.
                a. Run the remove_snapshot command.
                b. Assert that there are no errors.
                c. Wait for the plan to finish.
            9. Remove the named snapshot.
                a. Run the remove_snapshot command with the
                            'name' property given as an argument.
                b. Assert that there are no errors.
                c. Wait for the plan to finish.
        """
        # 1. Check all modelled 'file-system' items on MS
        file_system = self.find(self.ms_node, "/infrastructure",
                                   "file-system", assert_not_empty=False)

        # 2. Get the item with path '.../root'
        fs_root_path = [s for s in file_system if "/root" in s][0]

        # 3. Get the 'snap_size' property's value to ensure it is not 0
        snap_size = self.get_props_from_url(
                    self.ms_node, fs_root_path, filter_prop="snap_size")

        # If the current 'snap_size' is not 0:
        if snap_size != 0:
            # 4. Check for any existing snapshots and remove them
            self._remove_all_snapshots()

            # 5. Change the 'snap_size' to ensure 2 snapshots will fit on disk
            # 5a. Store properties of path for restoration at the end of test
            self.backup_path_props(self.ms_node, fs_root_path)
            # 5b. Update the 'snap_size' property to 30
            props = "snap_size=5"
            self.execute_cli_update_cmd(self.ms_node, fs_root_path, props)

            # 6. Create a deployment snapshot
            # 6a. Run the create_snapshot command
            create_snapshot_cmd = self.cli.get_create_snapshot_cmd()
            self.run_command(self.ms_node,
                            create_snapshot_cmd, add_to_cleanup=False)

            # 6b. Assert that there are no errors
            stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
            self.assertNotEqual([], stdout)
            self.assertEqual([], stderr)
            self.assertEqual(0, rc)

            # 6c. Wait for the plan to finish
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE))

            # 7. Create a named snapshot
            args = '-n cisnap'
            # 7a. Run the create_snapshot command with the
            #                       'name' property given as an argument.
            create_snapshot_cmd = self.cli.get_create_snapshot_cmd(args)
            self.run_command(self.ms_node,
                            create_snapshot_cmd, add_to_cleanup=False)

            # 7b. Assert that there are no errors
            stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
            self.assertNotEqual([], stdout)
            self.assertEqual([], stderr)
            self.assertEqual(0, rc)

            # 7c. Wait for the plan to finish and check it hasn't failed
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE))

            # 8. Remove the deployment snapshot
            # 8a. Run the remove_snapshot command
            remove_snapshot_cmd = self.cli.get_remove_snapshot_cmd()
            self.run_command(self.ms_node,
                                remove_snapshot_cmd, add_to_cleanup=False)

            # 8b. Assert that there are no errors
            stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
            self.assertNotEqual([], stdout)
            self.assertEqual([], stderr)
            self.assertEqual(0, rc)

            # 8c. Wait for the plan to finish and check it hasn't failed
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE))

            # 9. Remove the named snapshot
            # 9a. Run the remove_snapshot command with the
            #                       'name' property given as an argument
            remove_snapshot_cmd = self.cli.get_remove_snapshot_cmd(args)
            self.run_command(self.ms_node,
                                remove_snapshot_cmd, add_to_cleanup=False)

            # 9b. Assert that there are no errors
            stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
            self.assertNotEqual([], stdout)
            self.assertEqual([], stderr)
            self.assertEqual(0, rc)

            # 9c. Wait for the plan to finish and check it hasn't failed
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE))
