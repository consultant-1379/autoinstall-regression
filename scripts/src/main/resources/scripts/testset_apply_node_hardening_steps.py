"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:    April 2017
@authors:  Eimhin Smyth, Justin Ulevicius
@summary:  Integration
"""

import test_constants
from litp_generic_test import GenericTest, attr


class ApplyNodeHardeningSteps(GenericTest):
    """
    These tests apply various node hardening steps
    """
    def setUp(self):
        """
        Runs before every test
        """
        super(ApplyNodeHardeningSteps, self).setUp()
        self.all_nodes = [self.get_management_node_filenames()[0]]
        for node in self.get_managed_node_filenames():
            self.all_nodes.append(node)

    def tearDown(self):
        """
        Runs after every test
        """
        super(ApplyNodeHardeningSteps, self).tearDown()
        fname = ("/tmp/a_testset_logging.LoggingChecks.test_03_ensure_no_"
                 "litp_logs_in_root_and_tmp_dirs.xml")
        cmd = "rm -f " + fname
        if self.remote_path_exists(self.all_nodes[0], fname):
            self.log("info", "Removing .xml files")
            self.run_command(self.all_nodes[0], cmd, su_root=True)

    def append_line_to_file(self, node, line, file_name):
        """
        Description:
        Appends a line at the end of a file
        Args:
            node (node): The node where the file to be ammended lives
            line (str): The line to be appended
            file_name (str): The name of the file to be changed
        """
        cmd = "echo '" + line + "' >> " + file_name
        self.std_checks(self.run_command(node, cmd, su_root=True))

    def change_str_in_file(self, node, old_string, new_string, file_name):
        """
        Description:
        Appends a string in a file with a different string by building
        and then running an sed command
        Args:
            node (node): The node where the file to be ammended lives
            old_string (str): The line to be replaced
            new_string (str): The new string
            file_name (str): The name of the file to be changed
        """
        cmd = "/bin/sed -i 's," + old_string + "," + new_string
        cmd += ",g' " + file_name
        self.std_checks(self.run_command(node, cmd, su_root=True))

    def insert_string_into_file(self, node, old_string, new_string, file_name):
        """
        Description:
        Writes a string to a file underneath a specified string
        Args:
            node (node): The node where the file to be ammended lives
            old_string (str): The line the new string will
                              be inserted under
            new_string (str): The line to be inserted
            file_name (str): The name of the file to be changed
        """
        new_string = old_string + "\\n" + new_string
        self.change_str_in_file(node, old_string, new_string, file_name)

    def std_checks(self, outs):
        """
        Description:
        Performs checks on std_out, std_err and return code
        Args:
            outs (list of strings) : a list containing std_out,
                                     std_err and return code
        """
        self.assertEquals(outs[0], [], "std_out is not empty: " + str(outs[0]))
        self.assertEquals([], outs[1], "std_err is not empty: " + str(outs[1]))
        self.assertEquals(0, outs[2], "non-zero return code: " + str(outs[2]))

    def set_password_expiry(self, node):
        """
        Description:
        Sets passwords for root and litp-admin to expire in 60 days.
        Args:
            node (node): The node to set password expiry on
        Steps:
        1. Set litp-admin password.
        2. Ensure command runs successfully.
        3. Set root password.
        4. Ensure command runs successfully.
        """
        exp_duration = '60'
        self.log("info", "Changing password expiry to {0} days."
                 .format(exp_duration))
        # 1. Set litp-admin password.
        self.std_checks(self.run_command(node, "chage -M {0} litp-admin"
                                         .format(exp_duration),
                                         su_root=True))

        # 3. Set root password.
        self.std_checks(self.run_command(node, "chage -M {0} root"
                                         .format(exp_duration), su_root=True))

    def add_firewall_rules(self):
        """
        Description:
        Adds two iptables rules:
        -Dropped iptables packets will be logged to a file.
        -Remove Cobbler port from iptables on the MS once all
         nodes have booted up.

        Steps:
        1. Create litp firewall plugin rule to log dropped iptables packets.
        2. Create litp firewall plugin rule to remove port 69, which is used
           by Cobbler.
        """
        node = self.all_nodes[0]
        ms_fw_node_config_path = self.find(node, "/ms",
                                           "firewall-node-config",
                                           assert_not_empty=False)

        # Create firewall-node-config if required.
        if not ms_fw_node_config_path:
            ms_fw_node_config_path = "/ms/configs/fw_config"
            cmd = "litp create -t firewall-node-config -p" \
                " " + ms_fw_node_config_path
            self.std_checks(self.run_command(node, cmd))

        # 1. Create litp firewall plugin rule to log dropped iptables packets.
        self.log("info", "Firewall rule for dropped iptables packets")
        fw_log_rule_name = '906 log'
        fw_rule_dir = 'fw_log_nh'
        cmd = 'litp create -t firewall-rule -p {0}/rules/{1} -o name=\"{2}\"'\
        ' limit=\"2/min\" jump=\"LOG\" log_level=\"warning\"'\
        ' log_prefix=\"IPTABLES_DROPPED_PACKET\"'.format(
            ms_fw_node_config_path[0],
            fw_rule_dir,
            fw_log_rule_name)
        self.std_checks(self.run_command(node, cmd))

        # 2. Create litp firewall plugin rule to remove port 69.
        # No need to ensure nodes are booted up.
        self.log("info", "Firewall rule to remove port 69 used by Cobbler.")
        fw_cobbler_rule_name = '905 cobbler'
        fw_rule_dir = 'fw_cobbler_nh'
        cmd = 'litp create -t firewall-rule -p {0}/rules/{1} -o name=\"{2}\"'\
              ' dport=\"69\" action=drop'.format(ms_fw_node_config_path[0],
                                                 fw_rule_dir,
                                                 fw_cobbler_rule_name)

        self.std_checks(self.run_command(node, cmd))

    def encrypt_grub_password(self, node):
        """
        Description:
        Encrypt password.
        Args:
            node (node): The node to encrypt grub password on
        Steps:
        1. Encrypt the password.
        """

        # 1. Encrypt the password.
        self.log("info", "Adding a grub password hash.")
        cmd = "/sbin/grub2-setpassword"
        expects_cmds = list()
        expects_cmds.append(self.get_expects_dict("Enter password:",
                                                  "@dm1nS3rv3r"))
        expects_cmds.append(self.get_expects_dict("Confirm password:",
                                                  "@dm1nS3rv3r"))
        std_out, std_err, rc = self.run_expects_command(node, cmd,
                                                 expects_cmds,
                                                 su_root=True)

        self.assertEqual([], std_out)
        self.assertEqual([], std_err)
        self.assertEqual(0, rc)

        # Test user.cfg contains GRUB2_PASSWORD
        cmd = "cat /boot/grub2/user.cfg"
        std_out, _, _ = self.run_command(node, cmd,
                                         default_asserts=True,
                                         su_root=True)

        self.assertTrue(self.is_text_in_list('GRUB2_PASSWORD', std_out),
                        "/boot/grub2/user.cfg does not contain GRUB2_PASSWORD")

    def verify_single_user_mode_pw_protected(self, node):
        """
        Description:
         Verify Single User Mode is password protected
        Args:
            node (node): The node to test on
        Steps:
        1. Attempt to change mode
        """

        self.log("info",
         "Ensure single user mode is password protected by default.")

        cmd = 'systemctl isolate rescue.target'
        expected_error = \
         'Failed to start rescue.target: Interactive authentication required.'
        _, std_err, rcode = self.run_command(node, cmd)

        self.assertTrue(expected_error in std_err,
                        "Expected authentication error not received")
        self.assertNotEqual(0, rcode)

    def disable_rabbitmq_login(self, node):
        """
        Description:
        Disable bash login for RabbitMQ.
        Args:
            node (node) : The node to disable rabitmq login on
        Steps:
        1. Run usermod command.
        2. Ensure user successfully disabled.
        """
        # 1. Run usermod command.
        cmd = '/usr/sbin/usermod -s /sbin/nologin rabbitmq'
        _, _, rcode = self.run_command(node, cmd, su_root=True)
        # 2. Ensure user successfully disabled.
        self.assertEqual(0, rcode)

    def set_idle_timeout(self):
        """
        Description:
        Ensures idle sessions times out after 15 mins
        """
        self.log("info", "Ensuring idle sessions time out after 15 minutes.")
        lines = ['"readonly TMOUT=900"',
                 '"readonly HISTFILE"']
        f_name = "/etc/profile.d/os-security.sh"
        cmd_strings = ['echo ' + lines[0] + ' >| ' + f_name,
                       'echo ' + lines[1] + ' >> ' + f_name,
                       'chmod +x /etc/profile.d/os-security.sh']
        for node in self.all_nodes:
            for cmd in cmd_strings:
                self.log("info", "Running on node: " + node)
                self.std_checks(self.run_command(node, cmd, su_root=True))

    def prevent_password_reuse(self):
        """
        Description:
        Ensures that a new password is not the same as
        any of the last 5 passwords set
        """
        old_line = "pam_unix.so try_first_pass"
        old_line += " use_authtok nullok sha512 shadow"
        new_line = old_line + " remember=5"
        f_name = "/etc/pam.d/system-auth"
        self.log("info", "Disabling password reuse.")
        for node in self.all_nodes:
            self.change_str_in_file(node, old_line, new_line, f_name)

    def enforce_strong_passwords(self):
        """
        Description:
        Ensures that password length is 7 or greater and that
        passwords contain at least 3 types of characters
        """
        line = "password    requisite     pam_cracklib.so try_first_pass"
        line += " retry=3 minlen=7 minclass=3"
        self.log("info", "Setting up password strength rules.")
        for node in self.all_nodes:
            self.append_line_to_file(node, line, "/etc/pam.d/system-auth")

    def apply_and_verify_mesg(self):
        """
        Description:
        Stops other users from displaying messages to the terminal
        """
        self.log("info", "Disabling users from showing messages in terminal.")
        cmds = ["echo \"tty -s && mesg n\" >> /etc/profile",
                "echo \"tty -s && mesg n\" >> /etc/bashrc"]
        for node in self.all_nodes:
            for cmd in cmds:
                self.std_checks(self.run_command(node, cmd, su_root=True))

    def expire_accounts(self):
        """
        Description:
        Expires the accounts "halt", "shutdown" and "sync"
        """
        accounts_to_expire = ["halt", "shutdown", "sync"]
        for node in self.all_nodes:
            for account in accounts_to_expire:
                self.log("info", "Expiring account: {0}".format(account))
                cmd = "chage -E 1 " + account
                self.std_checks(self.run_command(node, cmd, su_root=True))

    def disallow_chfn_chsh(self):
        """
        Description:
        Stops non-root users from executing chfn and chsh commands
        """
        for node in self.all_nodes:
            self.log("info", "Disabling chfn command on: {0}".format(node))
            self.std_checks(self.run_command(node, "chmod 4700 /usr/bin/chfn",
                                             su_root=True))
            self.log("info", "Disabling chsh command on : {0}".format(node))
            self.std_checks(self.run_command(node, "chmod 4700 /usr/bin/chsh",
                                             su_root=True))

    def expire_inactive_login(self):
        """
        Description:
        Locks inactive accounts
        """
        new_string = "auth required pam_lastlog.so inactive=30"
        file_name = "/etc/pam.d/login"
        old_string = "auth       include      system-auth"
        self.log("info", "Disabling inactive accounts.")
        for node in self.all_nodes:
            self.insert_string_into_file(node, old_string,
                                         new_string, file_name)

    def edit_umask_settings(self):
        """
        Description:
        Increases umask threshold
        """
        for node in self.all_nodes:
            self.log("info", "Increase umask threshold on : {0}".format(node))
            self.change_str_in_file(node, "umask 002", "umask 027",
                                    "/etc/bashrc")
            self.change_str_in_file(node, "umask 002", "umask 027",
                                    "/etc/profile")

    def lock_account_after_failed_attempts(self):
        """
        Description:
        Locks accounts after repeated failed attempts
        """
        new_lines = ("auth\\trequired\\tpam_faillock.so preauth silent "
                     "audit deny=5 unlock_time=21600\\nauth\\tsufficient"
                     "\\tpam_unix.so nullok try_first_pass\\nauth\\t"
                     "[default=die]\\tpam_faillock.so authfail audit "
                     "deny=5 unlock_time=21600")
        line_to_insert_under = "auth        sufficient    pam_unix.so"
        line_to_insert_under += " try_first_pass nullok"
        for node in self.all_nodes:
            self.log("info",
                     "Enabling account locking after failed attempts on :{0}"
                     .format(node))
            self.insert_string_into_file(node, line_to_insert_under,
                                         new_lines, "/etc/pam.d/system-auth")
            self.insert_string_into_file(node, line_to_insert_under,
                                         new_lines,
                                         "/etc/pam.d/password-auth")

    def restrict_number_of_shells(self):
        """
        Description:
        Prevents litp-admin user from having more than 3 shells
        open at a time
        """
        insert_string = "litp-admin  -  maxlogins  3"
        f_name = "/etc/security/limits.conf"
        cmd = "echo '" + insert_string + "' >> " + f_name
        for node in self.all_nodes:
            self.std_checks(self.run_command(node, cmd, su_root=True))

    def update_routing_configuration(self):
        """
        Description:
        Defends against rogue ipv6 router advertisment
        """
        keys = ["net.ipv6.conf.default.autoconf",
                "net.ipv6.conf.default.accept_ra",
                "net.ipv6.conf.default.accept_ra_defrtr",
                "net.ipv6.conf.default.accept_ra_rtr_pref",
                "net.ipv6.conf.default.accept_ra_pinfo",
                "net.ipv6.conf.default.accept_source_route",
                "net.ipv6.conf.default.accept_redirects",

                "net.ipv6.conf.all.autoconf",
                "net.ipv6.conf.all.accept_ra",
                "net.ipv6.conf.all.accept_ra_defrtr",
                "net.ipv6.conf.all.accept_ra_rtr_pref",
                "net.ipv6.conf.all.accept_ra_pinfo",
                "net.ipv6.conf.all.accept_source_route",
                "net.ipv6.conf.all.accept_redirects"]

        value = 0
        #get the path to sysparams for each node
        paths = self.find(self.all_nodes[0], "/", "collection-of-sysparam")
        self.log("info", "Updating routing configuration.")
        for path in paths:
            #base command to create sysparams
            base_cmd = "litp create -t sysparam -p " + path + "/sysctl00"
            #counter for ensuring sysparams have unique names
            i = 0
            #runs a command creating a sysparam for each key
            for key in keys:
                key_value_string = "key=" + key + " value=" + str(value)
                cmd_to_run = base_cmd + str(i) + " -o " + key_value_string
                self.std_checks(self.run_command(self.all_nodes[0],
                                                 cmd_to_run))
                i += 1

    def create_and_run_plan(self):
        """
        Description:
        This step creates and runs a plan and waits for plan completion.
        """
        self.log("info", "Creating LITP plan...")
        self.execute_cli_createplan_cmd(self.all_nodes[0])
        self.log("info", "Running LITP plan...")
        self.execute_cli_runplan_cmd(self.all_nodes[0], add_to_cleanup=False)
        self.log("info", "Waiting for plan completion...")
        result = self.wait_for_plan_state(self.all_nodes[0],
                                          test_constants.PLAN_TASKS_SUCCESS,
                                          timeout_mins=30)
        self.assertTrue(result, "Plan did not succeed within 30 minutes")

    @attr("all", "hardening", "shell", "non-revert")
    def test_01_p_update_login_and_shell_settings(self):
        """
            Description:
                Applies various node hardening steps related to
                shell and login settings. Steps are
                as follows:

                -set idle timeout
                -prevent password reuse
                -enforce strong passwords
                -edit mesg settings
                -expire unused accounts
                -disallow chfn chsh commands
                -expire inactive logins
                -edit umask settings
                -verify single user mode is password protected
                -lock accoutns after failed attempts
                -restrict number of shells
                -set password expiry time
                -disable RabbitMQ login
                -encrypt grub password
        """
        self.log("info", "#################################################")
        self.log("info", "RUNNING SHELL AND LOGIN NODE HARDENING STEPS")
        self.log("info", "#################################################")
        self.set_idle_timeout()
        self.prevent_password_reuse()
        self.enforce_strong_passwords()
        self.apply_and_verify_mesg()
        self.expire_accounts()
        self.disallow_chfn_chsh()
        self.expire_inactive_login()
        self.edit_umask_settings()
        self.lock_account_after_failed_attempts()
        self.restrict_number_of_shells()
        self.disable_rabbitmq_login(self.all_nodes[0])
        for node in self.all_nodes:
            self.encrypt_grub_password(node)
            self.verify_single_user_mode_pw_protected(node)
            #this step breaks cloud installs, only
            #run on physical environments
            if self.get_running_env(self.all_nodes[0]) == 1:
                self.set_password_expiry(node)

    @attr("all", "hardening", "network", "non-revert")
    def test_02_p_update_network_settings(self):
        """
            Description:
                Applies various node hardening steps related to
                networking and firewalls. Steps are
                as follows:

                -update routing configuration,
                 this step helps defend against
                 rogue ipv6 router advertisment
                -add firewall rules, this step
                 sets up logging of all dropped
                 iptables packets and also disables
                 listening on 443 which is normally
                 used by cobbler
        """
        self.log("info", "#################################################")
        self.log("info", "RUNNING NETWORK AND FIREWALL NODE HARDENING STEPS")
        self.log("info", "#################################################")
        #Get a list of all sysparams
        sysparams = self.find(self.all_nodes[0], "/", "sysparam")
        test_key = "net.ipv6.conf.default.accept_ra_pinfo"
        skip_step = False
        #iterate list, checking if a key already exists
        #if key does exist, we can safely assume that this step
        #has already been applied, so we set skip_step
        for param in sysparams:
            if skip_step:
                break
            show_command = "litp show -p " + param
            std_out, _, _ = self.run_command(self.all_nodes[0], show_command)
            for line in std_out:
                if test_key in line:
                    self.log("info", "Routing config already updated")
                    skip_step = True
                    break
        #update routing config only if our test key
        #doesn't already exist
        if not skip_step:
            self.update_routing_configuration()
        self.add_firewall_rules()
        self.create_and_run_plan()
