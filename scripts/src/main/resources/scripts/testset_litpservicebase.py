"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    James Langan
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from litp_cli_utils import CLIUtils
import test_constants


class LitpServiceBase(GenericTest):
    """
    Test the LITP Service Base in LITP.
    Item Types verified are 'litp-service-base' extended items:
        'import-iso'
        'logging'
        'maintenance'
        'prepare_restore'
        'restore'
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(LitpServiceBase, self).setUp()

        self.ms_node = self.get_management_node_filename()
        self.rhcmd = RHCmdUtils()
        self.cli = CLIUtils()

    def tearDown(self):
        """ Teardown run after every test """

        super(LitpServiceBase, self).tearDown()

    def _check_msg_in_system_log(self, node, log_len, msg_str,
                                       log_file='/var/log/messages'):
        """
        Check that a message appears in the message log.
        Will tail the log from the current point backwards to 'log_len'.
        In other words, log_len is the start position in the log and
        curr_log_pos is the end position.

        Args:
           node (str): The node whose log you wish to check.

           log_len (str): Position in log to begin check.

           msg_str (str): The message in question.

       Kwargs:
           log_file (str): Path to the log file in question,
                           defaults to /var/log/messages.

        Returns:
        bool. True if found or False if not found.
        """
        log_path = log_file
        # Get current log length
        curr_log_pos = self.get_file_len(node, log_path)
        # Length of log to tail is current log length - old log length.
        test_logs_len = curr_log_pos - log_len
        cmd = self.rhcmd.get_grep_file_cmd(log_path, msg_str,
                                   file_access_cmd="tail -n {0}"
                                   .format(test_logs_len))
        _, err, ret_code = self.run_command(node, cmd,
                                              su_root=True)

        self.assertTrue(ret_code < 2)
        self.assertEqual([], err)
        if ret_code == 0:
            return True
        else:
            return False

    @attr('all', 'revert', 'system_check', 'litpservices', 'litpservices_tc01')
    def test_01_p_verify_litpservicebase(self):
        """
        Description:
            Verify that all the 'litp-service-base' extended item types
            modelled in LITP are configured appropriately:
                'import-iso'
                'logging'
                'maintenance'
                'prepare_restore'
                'restore'.
        Actions:
            1. Verify 'maintenance' item type.
            2. Verify 'logging' item type.
        """
        litp_url = '/litp'

        # Decision to leave testing of 'import-iso', 'prepare-restore' and
        # 'restore' until a later date'.
        base_list = {'logging': ['force_debug'],
                     'maintenance': ['enabled']}
                     #'import-iso': ['source_path'],
                     #'prepare-restore': ['actions', 'path'],
                     #'restore': ['update_trigger']}

        for item in base_list:
            url = self.find(self.ms_node, litp_url, item)[0]
            self.log("info", "Verifying '" + item + "' item type")

            props = self.get_props_from_url(self.ms_node, url)
            for prop in base_list[item]:
                self.log("info", "Verifying '" + prop + "' prop present")
                self.assertTrue(prop in props)

            # LITP Should never be in maintenance mode after install/upgrade
            # or expansion.
            if "maintenance" in url:
                self.assertEqual('false', props['enabled'],
                                 "WARNING: LITP in Maintenance Mode!!!")

            if "logging" in url:
                log_len = self.get_file_len(self.ms_node,
                                            test_constants.GEN_SYSTEM_LOG_PATH)
                expected_msg = 'DEBUG:'

                # Execute a command which will trigger DEBUG tracing if enabled
                cmd = self.cli.get_litp_version_cmd()
                _, std_err, rc = self.run_command(self.ms_node, cmd)
                self.assertEqual(0, rc)
                self.assertEqual([], std_err)

                # check /var/log/messages for DEBUG:
                result = self._check_msg_in_system_log(self.ms_node,
                                                       log_len, expected_msg)

                if props['force_debug'] == 'true':
                    # Verify that DEBUG tracing is visible in log.
                    # Puppet will trigger DEBUG tracing in log file.
                    self.log("info", "Verifying DEBUG tracing in system log")
                    self.assertTrue(result, "NO DEBUG tracing found in log")
                else:
                    # Verify that no DEBUG tracing is visible in log.
                    self.log("info", "Verifying NO DEBUG tracing in sys log")
                    self.assertFalse(result, "DEBUG tracing found in log")
