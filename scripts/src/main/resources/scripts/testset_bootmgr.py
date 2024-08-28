"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    Marco Gibboni
"""

from litp_generic_test import GenericTest, attr


class BootManager(GenericTest):
    """
    Test the BootManager LITP extension type.
    """

    def setUp(self):
        """ Setup Variables for every test """
        super(BootManager, self).setUp()
        self.model = self.get_model_names_and_urls()
        self.all_nodes = self.model["nodes"][:]
        self.ms_node = self.model["ms"][0]
        self.bootmgr_props = sorted([
                            'authentication',
                            'boot_mode',
                            'ksm_ksname',
                            'ksm_path',
                            'ksm_selinux_mode',
                            'manage_dhcp',
                            'manage_dns',
                            'puppet_auto_setup',
                            'pxe_boot_timeout',
                            'remove_old_puppet_certs_automatically',
                            'rsync_disabled',
                            'sign_puppet_certs_automatically'
                        ])

    def tearDown(self):
        """ Teardown run after every test """
        super(BootManager, self).tearDown()

    def compare_boot_props(self, props_list):
        """
            This function compares the expected
            properties with the list name
            passed as parameter
        """
        for key in range(0, len(self.bootmgr_props)):
            if self.bootmgr_props[key] != props_list[key]:
                self.log('info', "The property '{0}' is missing!"\
                        .format(self.bootmgr_props[key]))
                return False
        return True

    @attr('all', 'revert', 'system_check', 'bootmgr', 'bootmgr_tc01')
    def test_01_check_cobbler_props(self):
        """
        Description:
            A. Check if the cobbler-service item is created
                    with all its properties
            B. Check whether the cobblerd service is running on MS
            C. Check the property values
        Actions:
            A
                1. Retrieve the cobbler-service item and
                    assert there's no more than one of it.
                2. Check if all the properties are set

            B   1. Run service status command on MS to
                    check whether cobblerd service
                    is running
            C
                1. Check if the ksm path exists
                2. Check if the ksm peer node files exist
                3. Check selinux value in peer nodes ks files
                4. Run selinuxenabled command to confirm
        """
        # A1. Retrieve the cobbler-service item and
        #       assert there's no more than one of it.
        cobbler = self.find(self.ms_node['name'], \
                    self.ms_node['url'], "cobbler-service")
        self.assertTrue(len(cobbler) <= 1)
        if not cobbler:
            self.log('info', "There's no cobbler service.")
        else:
            cobbler = cobbler[0]
            prop_values = self.get_props_from_url(\
                            self.ms_node['name'], cobbler)
            # A2. Check if all the properties are set
            prop_names = prop_values.keys()
            same_lists = self.compare_boot_props(sorted(prop_names))
            self.assertTrue(same_lists)
            self.log('info', "All the required properties are set.")
            # B1. Run service status command on MS to
            #       check whether cobblerd service
            #       is running
            _, std_err, r_code = \
                self.get_service_status(self.ms_node['name'], 'cobblerd')
            self.assertEqual([], std_err)
            self.assertEqual(0, r_code)
            # C1. Check if the ksm path exists
            is_path = self.remote_path_exists(self.ms_node['name'], \
                                                prop_values['ksm_path'], \
                                                expect_file=False)
            self.assertTrue(is_path)
            self.log('info', "Kickstart path exists!")
            # C2. Check if the peer node ks files exist
            for node in self.all_nodes:
                ks_file = "{0}/{1}.ks"\
                            .format(prop_values['ksm_path'], node['name'])
                file_exists = self.remote_path_exists(\
                                self.ms_node['name'], ks_file)
                self.assertTrue(file_exists)
                self.log('info', "Kickstart file '{0}.ks' \
                                    exists!".format(node['name']))
                # C3. Check selinux value in peer nodes ks files
                file_contents = self.get_file_contents(self.ms_node['name'], \
                                "{0}/{1}.ks".format(prop_values['ksm_path'], \
                                                        node['name']))
                self.assertTrue(self.is_text_in_list('selinux --{0}'\
                    .format(prop_values['ksm_selinux_mode']), file_contents))
            # C4. Run selinuxenabled command to confirm
            cmd = "/usr/sbin/selinuxenabled"
            _, _, r_code = self.run_command(self.ms_node['name'], cmd,
                                                            su_root=True)
            self.assertEqual(0, r_code)
