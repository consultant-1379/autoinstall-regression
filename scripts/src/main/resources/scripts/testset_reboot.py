"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     November 2015
@author:    Bryan O'Neill
"""

from litp_generic_test import GenericTest, attr
import test_constants
import os


class TestReboot(GenericTest):
    """
    Test the Rebooting of nodes and running succeding tasks..
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(TestReboot, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.all_nodes = self.mn_nodes + [self.ms_node]

    def teardown(self):
        """ Teardown run after every test """

        super(TestReboot, self).tearDown()

    @attr('all', 'revert', 'system_functionality', 'reboot', 'reboot_tc01')
    def test_reboot_01(self):
        """
        Description:
            Test the reboot of node and tasks after the reboot phase.
        Actions:
            # 1: Install the initial version of the rpm
            # 2: Copy the upgrade rpm to the MS
            # 3: Import the updated rpm
            # 4: Upgrade using yum
            # 5: Mark deployment for upgrade
            # 6: Execute create plan
            # 7: Run Plan
        """
        rpm_dir = os.path.join(os.path.dirname(__file__), 'reboot_rpms')
        base_rpm = os.path.join(rpm_dir, 'popcorn-kernel-1.0-1.el6.x86_64.rpm')
        upgrade_rpm = os.path.join(rpm_dir,
                                   'popcorn-kernel-1.1-1.el6.x86_64.rpm')

        deployment = self.find(self.ms_node, '/deployments', 'deployment')[0]

        # Optional: Remove rpm from all nodes
        # Uncomment this section of code if there is a need to run this test in
        # a loop.
        # self.log('info', "Removing popcorn-kernel package from all nodes")
        # for node in self.all_nodes:
        #     self.wait_for_node_up(node)
        #     self.remove_rpm_on_node(node, 'popcorn-kernel')

        # 1: Install the initial version of the rpm
        for node in self.all_nodes:
            self.assertTrue(
                self.copy_and_install_rpms(node, [base_rpm], '/tmp'))

        # 2: Copy the upgrade rpm to the MS
        self.assertTrue(
            self.copy_file_to(self.ms_node, upgrade_rpm, '/tmp'))

        # 3: Import the updated rpm
        self.execute_cli_import_cmd(
            self.ms_node, '/tmp/popcorn-kernel-1.1-1.el6.x86_64.rpm',
            test_constants.OS_UPDATES_PATH_RHEL7)

        # 4: Upgrade using yum
        stdout, stderr, rc = self.run_command(
            self.ms_node,
            '/usr/bin/yum  --disablerepo=* --enablerepo=UPDATES '
            'upgrade -y', su_root=True, add_to_cleanup=False)
        self.assertEqual(0, rc)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

        # 5: Mark deployment for upgrade
        self.execute_cli_upgrade_cmd(self.ms_node, deployment)

        # 6: Execute create plan
        self.execute_cli_createplan_cmd(self.ms_node)

        # 7: Run Plan
        self.execute_cli_runplan_cmd(self.ms_node, add_to_cleanup=False)

        result = self.wait_for_plan_state(self.ms_node,
                                          test_constants.PLAN_COMPLETE,
                                          timeout_mins=30)
        self.assertTrue(result)
