"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:      2015
@author: Cristiane Rocha
"""

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils


class AppliedState(GenericTest):
    """
    This class tests if all items have their state as Applied.
    """

    def setUp(self):
        """ Setup Variables for every test """
        super(AppliedState, self).setUp()
        # GET MODEL INFO
        self.ms_node = self.get_management_node_filename()
        self.cli = CLIUtils()

    def tearDown(self):
        """ Teardown run after every test """
        super(AppliedState, self).tearDown()

    @attr('all', 'revert', 'system_check', 'appliedstate', 'appliedstate_tc01')
    def test_01_check_applied_state(self):
        """
        Description:
        A. Find all item types into LITP Model with status equal Applied

        Actions:
        A.
            1. Find all urls from the litp model
            2. Assert state = Applied

        """
        remove_plan_cmd = self.cli.get_remove_plan_cmd()
        self.run_command(self.ms_node, remove_plan_cmd)
        ignore_paths = []
        ignore_paths.extend(self.find(self.ms_node, "/", "upgrade",
                                  assert_not_empty=False))
        ignore_paths.extend(self.find(self.ms_node, "/", "deployment",
                                  assert_not_empty=False))
        self.assertTrue(self.is_all_applied(self.ms_node, ignore_paths))
