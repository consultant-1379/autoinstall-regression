"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     August 2015
@author:    Laura Forbes
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from litp_cli_utils import CLIUtils
import test_constants
import os


class LITPCommands(GenericTest):
    """
    Test the core functionality of LITP using a dummy plugin.
    CLI commands tested: create, create_plan, import, inherit, remove,
                    run_plan, show, show_plan, stop_plan, update, and version.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(LITPCommands, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]
        self.all_nodes = self.model["nodes"][:]
        self.all_nodes.extend(self.model["ms"][:])
        self.redhatutils = RHCmdUtils()
        self.cli = CLIUtils()

        # Define item types and URLs
        self.config_class = "test-config"
        self.config_url = "/software/items/test_config"
        self.callback_class = "test-callback"
        self.callback_url = "/software/items/test_callback"
        self.remote_class = "test-remote-execution"
        self.remote_url = "/software/items/test_remote"
        self.ordered_class = "test-ordered-list"
        self.ordered_url = "/software/items/test_ordered"

    def tearDown(self):
        """ Teardown run after every test """

        super(LITPCommands, self).tearDown()

    def _create_item(self, url, class_type, props_dict):
        """
        Description:
            Create an item in the model.
            Ensure the item is in state "Initial".
            Ensure the properties created are present in the item.

        Args:
            url (str): Path to where item will be created.
            class_type (str): Type of item to create.
            props_dict (dict): Dictionary of property names and values.

        Actions:
            a. Arrange properties into correct format for create command.
            b. Execute create command with properties given.
            c. Ensure item state is "Initial".
            d. Ensure properties created are present in item.
        """
        # a. Arrange properties into correct format for create command.
        props = ""
        for key, value in props_dict.iteritems():
            props += "{0}={1} ".format(key, value)

        # b. Execute create command with properties.
        _, stderr, rc = self.execute_cli_create_cmd(
            self.ms_node, url, class_type, props)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # c. Ensure item state is "Initial".
        item_state = self.get_item_state(self.ms_node, url)
        self.assertTrue("Initial" in item_state)

        # d. Ensure properties created are present in item.
        check_props = self.get_props_from_url(self.ms_node, url)
        for value in props_dict.values():
            self.assertTrue(value in check_props.values())

    def _remove_item(self, url):
        """
        Description:
            Remove an item on the given path.
            Check the model to ensure the item has been removed successfully.

        Args:
            url (str): Path of item to be removed.

        Actions:
            a. Remove item on given path.
            b. Ensure the item has been removed from model.
        """
        # a. Remove item on given path.
        _, stderr, rc = self.execute_cli_remove_cmd(self.ms_node, url)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # b. Ensure the item has been removed from model.
        _, stderr, rc = self.execute_cli_show_cmd(
                    self.ms_node, url, expect_positive=False)
        self.assertEqual(rc, 1)
        self.assertTrue(any("InvalidLocationError" in s for s in stderr))

    def _remove_def_property(self, url, prop_name, def_prop):
        """
        Description:
            Remove specified default property from the item on the given path.
            Ensure property is replaced with default value.

        Args:
            url (str): Path to item with property to be removed.
            prop_name (str): Name of the property to be removed.
            def_prop (str): Value that property should default to when removed.

        Actions:
            a. Remove specified property from the item on given path.
            b. Ensure property is replaced with default value.
        """
        # a. Remove specified property from the item on given path.
        _, stderr, rc = self.execute_cli_update_cmd(
                    self.ms_node, url, prop_name, action_del=True)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # b. Ensure property is replaced with default value.
        check_props = self.get_props_from_url(self.ms_node, url)
        self.assertTrue(def_prop in check_props.values())

    def _update_property(self, url, prop_name, prop_value):
        """
        Description:
            Update specified property with given value.
            Ensure value of property has been updated successfully.

        Args:
            url (str): Path to item with property to be updated.
            prop_name (str): Name of the property to be updated.
            prop_value (str): Value that the property will be updated to.

        Actions:
            a. Update specified property in given path.
            b. Check that the item has been successfully updated to new value.
        """
        # a. Update specified property in given path.
        _, stderr, rc = self.execute_cli_update_cmd(
            self.ms_node, url, "{0}={1}".format(prop_name, prop_value))
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # b. Check that the item has been successfully updated to new value.
        check_props = self.get_props_from_url(self.ms_node, url, prop_name)
        self.assertEqual(check_props, prop_value)

    def _create_invalid_item(self, url, class_type, invalid_props):
        """
        Description:
            Attempt to create an item with invalid property values.
            Check that each property gives an error.
            Check that the item is not created in the model.

        Args:
            url (str): Path to where item will be created.
            class_type (str): Type of item to create.
            invalid_props (dict): Property names and invalid values.

        Actions:
            a. Arrange properties into correct format for create command.
            b. Execute create command with invalid properties.
            c. Check that each property gives an error.
            d. Check that the item is not created in the model.
        """
        # a. Arrange properties into correct format for create command.
        props = ""
        for key, value in invalid_props.iteritems():
            props += "{0}={1} ".format(key, value)

        # b. Execute create command with invalid properties.
        _, stderr, rc = self.execute_cli_create_cmd(
            self.ms_node, url, class_type, props, expect_positive=False)
        self.assertNotEqual(stderr, [])
        self.assertEqual(rc, 1)

        # c. Check that each property gives an error.
        for key in invalid_props:
            check_error = 'ValidationError in property: \"{0}\"'.format(key)
            self.assertTrue(any(check_error in s for s in stderr))

        # d. Check that the item is not created in the model.
        _, stderr, rc = self.execute_cli_show_cmd(
            self.ms_node, url, expect_positive=False)
        self.assertEqual(rc, 1)
        self.assertTrue(any("InvalidLocationError" in s for s in stderr))

    @attr('all', 'revert', 'system_functionality', 'LITPCommands',
          'LITPCommands_tc01')
    def test_p_litp_import_command(self):
        """
        Description:
            Copy the LITP compliant RPMs (plugins) to the MS.
            Import and install the RPMs.
            Check that the RPMs installed successfully.
            Check that the LITP packages were installed successfully.

        Actions:
            1. Copy the RPMs to the MS.
            2. Import the RPMs.
            3. Install the RPMs.
            4. Check that the RPMs are installed successfully.
            5. Run "litp version -a" and ensure the packages are present.
        """
        # Define plugin and pluginapi RPM names.
        plugin = "ERIClitptest_plugin_CXP02-1.0.1-202109201203.noarch.rpm"
        pluginapi =\
            "ERIClitptest_pluginapi_CXP01-1.0.1-202109101559.noarch.rpm"

        plugin_folder = "/test_rpms/"
        plugin_path = os.path.dirname(os.path.realpath(__file__))\
                      + plugin_folder + plugin
        plugin_api_path = os.path.dirname(os.path.realpath(__file__))\
                          + plugin_folder + pluginapi

        # 1. Copy the RPMs to the MS.
        self.assertTrue(self.copy_file_to(
            self.ms_node, plugin_path, "/tmp/"))
        self.assertTrue(self.copy_file_to(
            self.ms_node, plugin_api_path, "/tmp/"))

        # 2. Import the RPMs.
        self.execute_cli_import_cmd(
            self.ms_node, "/tmp/" + plugin, "litp")
        self.execute_cli_import_cmd(
            self.ms_node, "/tmp/" + pluginapi, "litp")

        # 3. Install the RPMs
        self.assertTrue(
            self.install_rpm_on_node(self.ms_node, plugin.split("-")[0]))
        self.assertTrue(
            self.install_rpm_on_node(self.ms_node, pluginapi.split("-")[0]))

        # 4. Check that the packages installed successfully.
        check_installed = [plugin.rsplit('.', 1)[0],
                           pluginapi.rsplit('.', 1)[0]]

        cmd = self.redhatutils.check_pkg_installed(check_installed)
        _, stderr, rc = self.run_command(self.ms_node, cmd)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # 5. Run "litp version -a" and ensure the packages are present.
        cmd = self.cli.get_litp_version_cmd(args='-a')
        stdout, stderr, rc = self.run_command(self.ms_node, cmd)
        self.assertEqual(0, rc)
        self.assertEqual([], stderr)
        self.assertTrue(any(
            "ERIClitptest_plugin: 1.0.1" in s for s in stdout))
        self.assertTrue(any(
            "ERIClitptest_pluginapi: 1.0.1" in s for s in stdout))

    @attr('all', 'revert', 'system_functionality', 'LITPCommands',
          'LITPCommands_tc02')
    def test_p_litp_create_remove_items(self):
        """
        Description:
            Create item for each item type in the plugin with mandatory props.
            Check that these items are in an "Initial" state and the
                                properties that were created are present.
            Remove these items and ensure they are no longer in the model.
            Create an item with a value for the default property.
            Check that the item is in an "Initial" state and the
                                default property is present.
            Remove the inputted value from the default property of the item.
            Check that the property's value is now set to its default value.
            Update an optional property of the item.
            Check that the property has been updated to the new value.
            Remove the item and ensure it is no longer in the model.

        Actions:
            1. Create a test-config item with mandatory properties
                    ensuring properties created are present in item.
            2. Create a test-callback item with mandatory properties
                    ensuring properties created are present in item.
            3. Create a test-remote-execution item with mandatory properties
                    ensuring properties created are present in item.
            4. Create a test-ordered-list item with mandatory properties
                    ensuring properties created are present in item.
            5. Remove all of the created items and
                    ensure they have been removed from the model.
            6. Create a test-config item with a value for the default property.
            7. Remove the default property of the item.
            8. Update an optional property of the item.
            9. Remove the item.
        """
        # 1. Create a test-config item with mandatory properties ensuring
        #        properties created are present in item.
        config_props = {'mand_prop_1': 'test-config-1'}
        self._create_item(self.config_url, self.config_class, config_props)

        # 2. Create a test-callback item with mandatory properties ensuring
        #        properties created are present in item.
        callback_props = {'mand_prop_1': 'test-callback-1'}
        self._create_item(self.callback_url,
                          self.callback_class, callback_props)

        # 3. Create a test-remote-execution item with mandatory properties
        #       ensuring properties created are present in item.
        remote_props = {'mand_prop_1': 'test-remote-1'}
        self._create_item(self.remote_url, self.remote_class, remote_props)

        # 4. Create a test-ordered-list item with mandatory properties ensuring
        #        properties created are present in item.
        ordered_props = {'mand_prop_1': 'test-ordered-1'}
        self._create_item(self.ordered_url, self.ordered_class, ordered_props)

        # 5. Remove all of the created items and
        #       ensure they have been removed from the model.
        self._remove_item(self.config_url)
        self._remove_item(self.callback_url)
        self._remove_item(self.remote_url)
        self._remove_item(self.ordered_url)

        # 6. Create a test-config item with a value for the default property.
        props_dict = {'mand_prop_1': 'test-plugin-1', 'def_prop_1': '0777',
                                                'opt_prop_1': 'old_optional'}
        self._create_item(self.config_url, self.config_class, props_dict)

        # 7. Remove the default property of the item.
        prop_name = "def_prop_1"
        def_prop = "0444"
        self._remove_def_property(self.config_url, prop_name, def_prop)

        # 8. Update an optional property of the item.
        prop_name = "opt_prop_1"
        prop_value = "new_optional"
        self._update_property(self.config_url, prop_name, prop_value)

        # 9. Remove the item.
        self._remove_item(self.config_url)

    @attr('all', 'revert', 'system_functionality', 'LITPCommands',
          'LITPCommands_tc03')
    def test_n_litp_create_validation(self):
        """
        Description:
            Attempt to create items with invalid properties.
            Ensure each property gives an error and the items are not created.

        Actions:
            1. Attempt to create a test-config item with invalid properties,
                ensure each property gives an error and the item is not created
            2. Attempt to create a test-callback item with invalid properties,
                ensure each property gives an error and the item is not created
            3. Attempt to create test-remote-execution item with invalid props,
                ensure each property gives an error and the item is not created
            4. Attempt to create a test-ordered-list item with invalid props,
                ensure each property gives an error and the item is not created
        """
        # 1. Attempt to create a test-config item with invalid properties,
        #       ensure each property gives an error and the item is not created
        config_invalid_props = {'mand_prop_1': 'testInvalid',
                                        'def_prop_1': 'invalidTest'}
        self._create_invalid_item(self.config_url,
                                  self.config_class, config_invalid_props)

        # 2. Attempt to create a test-callback item with invalid properties,
        #       ensure each property gives an error and the item is not created
        callback_invalid_props = {'mand_prop_1': '123', 'def_prop_1': '04'}
        self._create_invalid_item(self.callback_url,
                                  self.callback_class, callback_invalid_props)

        # 3. Attempt to create a test-remote-execution item with invalid props,
        #       ensure each property gives an error and the item is not created
        remote_invalid_props = {'mand_prop_1': 'test-config',
                                                    'def_prop_1': '04444'}
        self._create_invalid_item(self.remote_url,
                                    self.remote_class, remote_invalid_props)

        # 4. Attempt to create test-ordered-list item with invalid properties,
        #       ensure each property gives an error and the item is not created
        ordered_invalid_props = {'mand_prop_1': 'test_config_1'}
        self._create_invalid_item(self.ordered_url, self.ordered_class,
                                                        ordered_invalid_props)

        # Add an item type which has a read only property, try to create with
        #   that read only property, an error should be given

    @attr('all', 'revert', 'system_functionality', 'LITPCommands',
          'LITPCommands_tc04')
    def test_p_item_type_config_callback_remote_execution(self):
        """
        Description:
            Create test-config, test-callback and test-remote-execution
                    item types with mandatory properties.
            Inherit all items under the MS and one node.
            Create and run a plan checking that a file has
                    been created for each item type on each node.
            Update the optional property of the test-config item.
            Create and run a plan checking that the test-config
                    item's file has been updated with the new value.
            Remove the optional property of the test-config item.
            Create and run a plan checking that the test-config
                    file has been changed back to it's default value.
            Remove each inherited item and item type.
            Create and run a plan checking that all of the
                    item types and created files have been removed.
            Also tests stopping a plan and recreating it.

        Actions:
            1. Create a test-config item with mandatory and optional properties
                        ensuring the properties created are present in item.
            2. Create a test-callback item with mandatory property ensuring
                        properties created are present in item.
            3. Create a test-remote-execution item with mandatory property
                        ensuring properties created are present in item.
            4. Inherit each item under the MS and one node.
                a. Inherit test-config item under node.
                b. Inherit test-callback item under node.
                c. Inherit test-remote-execution item under node.
            5. Create a plan.
            6. Show plan to check that the correct expected tasks are present.
                a. Ensure each item and each node is in the plan.
                b. Ensure the plan creates a file for each item type.
            7. Run the plan.
                a. Wait for the plan to complete.
            8. Check that each item type is in state "Applied".
            9. Check that a file has been created for each item type.
            10. Update the value of the optional property of test-config item.
            11. Check that the state of the test-config item is "Updated".
            12. Update the value of the default property of test-callback item.
            13. Check that the state of the test-callback item is "Updated".
            14. Update the default property of test-callback item back
                        to it's original value.
            15. Check that the state of the test-callback item is "Applied".
            16. Create a plan.
            17. Get a list of tasks in state "Initial".
            18. Show plan to check that the correct expected tasks are present.
                a. Ensure the plan updates the test-config item's file.
                b. Ensure that test-callback is not being updated in the plan.
            19. Run the plan.
                a. Check the plan is running.
            20. Get a list of running tasks.
            21. Stop the plan.
                a.  Wait for plan to be in "Stopped" state.
            22. Get list of successful tasks.
            23. Compare running and successful tasks.
            24. Check all other tasks are in state "Initial".
                a. Get all tasks that are still in state "Initial".
                b. Check that tasks that were not run
                        are still in plan in state "Initial".
            25. Create a plan.
                a. Check that the successful tasks are not present in the plan.
                b. Check that all other initial tasks are present in the plan.
            26. Run the plan.
                a. Wait for the plan to complete.
            27. Check that the value in the test-config item's file has
                        been updated with the new value.
            28. Remove the optional property of the test-config item.
            29. Check that the state of the test-config item is "Updated".
            30. Create a plan.
            31. Show plan to check that the correct expected tasks are present.
                a. Ensure the plan updates the test-config item's file.
            32. Run the plan.
                a. Wait for the plan to complete.
            33. Check that the value in the test-config file has been
                        changed back to the default value of "None".
            34. Remove each inherited URL:
                a. Remove the item at the given URL.
                b. Check that the state of test-config item is "ForRemoval".
            35. Remove each item type:
                a. Remove the item at the given URL.
                b. Check that the state of test-config item is "ForRemoval".
            36. Create a plan.
            37. Show plan to check that the correct expected tasks are present.
                a. Ensure the URL of each inherited item is in the plan.
                b. Ensure the URL of each item type is in the plan.
                c. Ensure the plan deletes each item type's file.
            38. Run the plan.
                a. Wait for the plan to complete.
            39. Check that all item types are removed.
                a. Run a show command for each item.
                b. Assert that an "InvalidLocationError" error
                                                is returned from the command.
            40. Check that all of the created files have been removed.
        """
        # 1. Create a test-config item with mandatory and optional properties
        #       ensuring the properties created are present in item.
        config_props = {'mand_prop_1': 'test-config-1',
                                            'opt_prop_1': 'OldValue'}
        self._create_item(self.config_url, self.config_class, config_props)

        # 2. Create a test-callback item with mandatory property ensuring
        #       properties created are present in item.
        callback_props = {'mand_prop_1': 'test-callback-1'}
        self._create_item(self.callback_url,
                          self.callback_class, callback_props)

        # 3. Create a test-remote-execution item with mandatory property
        #       ensuring properties created are present in item.
        execution_url = "/software/items/test_exec"
        execution_class = "test-remote-execution"
        execution_props = {'mand_prop_1': 'test-exec-1'}
        self._create_item(execution_url, execution_class, execution_props)

        file_names = ["test-config-1", "test-callback-1", "test-exec-1"]
        item_urls = [self.config_url, self.callback_url, execution_url]
        # Create a list to check each item type is inherited under each node
        check_node_show = []
        # Create a list to contain URL of each item type and inherited item
        url_list = [self.config_url, self.callback_url, execution_url]

        # 4. Inherit each item under MS and one node
        test_nodes = [self.model["ms"][0], self.all_nodes[0]]

        for node in test_nodes:
            node_name = node["name"]
            # 4a. Inherit test-config item under node
            inherit_config_url = "{0}/items/test_config_{1}".format(
                                                        node["url"], node_name)
            self.execute_cli_inherit_cmd(
                self.ms_node, inherit_config_url, self.config_url)

            # 4b. Inherit test-callback item under node
            inherit_callback_url = "{0}/items/test_callback_{1}".format(
                                                        node["url"], node_name)
            self.execute_cli_inherit_cmd(
                self.ms_node, inherit_callback_url, self.callback_url)

            # 4c. Inherit test-remote-execution item under node
            inherit_execution_url = "{0}/items/test_exec_{1}".format(
                                                        node["url"], node_name)
            self.execute_cli_inherit_cmd(
                self.ms_node, inherit_execution_url, execution_url)

            check_node_show.extend(["test_config_{0}".format(node_name),
                                        "test_exec_{0}".format(node_name),
                                            "test_exec_{0}".format(node_name)])

            url_list.extend([inherit_config_url, inherit_callback_url,
                                                        inherit_execution_url])

        # 5. Create a plan
        self.execute_cli_createplan_cmd(self.ms_node)

        # 6. Show the plan to check that the correct expected tasks are present
        stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # 6a. Ensure each item and each node is in the plan
        for item in check_node_show:
            self.assertTrue(any(item in s for s in stdout))

        # 6b. Ensure the plan creates a file for each item type
        self.assertTrue(any("ConfigTask to create file /tmp/test-config-1"
                                                        in s for s in stdout))
        self.assertTrue(any("CallbackTask to create file /tmp/test-callback-1"
                                                        in s for s in stdout))
        self.assertTrue(any("RemoteExecutionTask to create file "
                            "/tmp/test-exec-1" in s for s in stdout))

        # 7. Run the plan
        self.execute_cli_runplan_cmd(self.ms_node)

        # 7a. Wait for the plan to complete
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_COMPLETE))

        # 8. Check that each item type is in state "Applied"
        for url in url_list:
            item_state = self.get_item_state(self.ms_node, url)
            self.assertTrue("Applied" in item_state)

        # 9. Check that a file has been created for each item type
        dir_contents = self.list_dir_contents(self.ms_node, "/tmp")
        for file_name in file_names:
            self.assertTrue(any(file_name in s for s in dir_contents))

        # 10. Update the value of the optional property of test-config item
        self._update_property(self.config_url, "opt_prop_1", "NewValue")

        # 11. Check that the state of the test-config item is "Updated"
        item_state = self.get_item_state(self.ms_node, self.config_url)
        self.assertTrue("Updated" in item_state)

        # 12. Update the value of the default property of test-callback item
        self._update_property(self.callback_url, "def_prop_1", "0777")

        # 13. Check that the state of the test-callback item is "Updated"
        item_state = self.get_item_state(self.ms_node, self.callback_url)
        self.assertTrue("Updated" in item_state)

        # 14. Update the default property of test-callback item back
        #           to it's original value
        self._update_property(self.callback_url, "def_prop_1", "0444")

        # 15. Check that the state of the test-callback item is "Applied"
        item_state = self.get_item_state(self.ms_node, self.callback_url)
        self.assertTrue("Applied" in item_state)

        # 16. Create a plan
        self.execute_cli_createplan_cmd(self.ms_node)

        # 17. Get a list of tasks in state "Initial"
        initial_tasks = self.get_plan_task_states(self.ms_node, 2)

        # 18. Show plan to check that the correct expected tasks are present
        stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # 18a. Ensure the plan updates the test-config item's file
        self.assertTrue(any("ConfigTask to update file /tmp/test-config-1"
                                                        in s for s in stdout))

        # 18b. Ensure that test-callback is not being updated in the plan
        self.assertTrue(any(inherit_callback_url not in s for s in stdout))

        # 19. Run the plan
        self.execute_cli_runplan_cmd(self.ms_node)

        # 19a. Check plan is running
        self.assertEqual(1, self.get_current_plan_state(self.ms_node))

        # 20. Get list of running tasks
        running_tasks = self.get_plan_task_states(self.ms_node, 3)

        # 21. Stop the plan
        self.execute_cli_stopplan_cmd(self.ms_node)

        # 21a. Wait for plan to be in stopped state
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_STOPPED))

        # 22. Get list of successful tasks
        successful_tasks = self.get_plan_task_states(self.ms_node, 0)

        # 23. Compare running and successful tasks
        self.assertTrue(sorted(running_tasks) == sorted(successful_tasks),
            "Running Tasks and Successful Tasks "
                "do not match after stopping plan.")

        # 24. Check all other tasks are in state "Initial"
        # 24a. Get all tasks that are still in state "Initial"
        initial_tasks_stopped = self.get_plan_task_states(self.ms_node, 2)

        # 24b. Check that tasks that were not run
        #           are still in plan in state "Initial"
        for entry in successful_tasks:
            initial_tasks.remove(entry)
        self.assertTrue(sorted(initial_tasks) == sorted(initial_tasks_stopped),
            "Initial Tasks do not match after stopping plan.")

        # 25. Create a plan
        self.execute_cli_createplan_cmd(self.ms_node)

        # Get a list of tasks in state "Initial"
        initial_tasks_recreate = self.get_plan_task_states(self.ms_node, 2)
        # 25a. Check that the successful tasks are not present in the plan
        self.assertFalse(
            any(x in successful_tasks for x in initial_tasks_recreate))

        # 25b. Check that all other initial tasks are present in the plan
        self.assertTrue(
            all(x in initial_tasks for x in initial_tasks_recreate))

        # 26. Run the plan
        self.execute_cli_runplan_cmd(self.ms_node)

        # 26a. Wait for the plan to complete
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_COMPLETE))

        # 27. Check that the value in the test-config item's
        #           file has been updated with the new value
        file_contents = self.get_file_contents(
            self.ms_node, "/tmp/test-config-1")
        self.assertTrue(any("NewValue" in s for s in file_contents))

        # 28. Remove the optional property of the test-config item
        _, stderr, rc = self.execute_cli_update_cmd(
                self.ms_node, self.config_url, "opt_prop_1", action_del=True)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # 29. Check that the state of the test-config item is "Updated"
        item_state = self.get_item_state(self.ms_node, self.config_url)
        self.assertTrue("Updated" in item_state)

        # 30. Create a plan
        self.execute_cli_createplan_cmd(self.ms_node)

        # 31. Show plan to check that the correct expected tasks are present
        stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # 31a. Ensure the plan updates the test-config item's file
        self.assertTrue(any("ConfigTask to update file /tmp/test-config-1"
                                                        in s for s in stdout))

        # 32. Run the plan
        self.execute_cli_runplan_cmd(self.ms_node)

        # 32a. Wait for the plan to complete
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_COMPLETE))

        # 33. Check that the value in the test-config file has
        #           been changed back to the default value of "None"
        file_contents = self.get_file_contents(
                            self.ms_node, "/tmp/test-config-1")
        self.assertTrue(any("None" in s for s in file_contents))

        # Remove the URLs of the item types from the URL list
        url_list = url_list[3:]

        # 34. Remove each inherited URL:
        for url in url_list:
            # 34a. Remove the item at the given URL
            self.execute_cli_remove_cmd(self.ms_node, url)
            # 34b. Check that the state of the test-config item is "ForRemoval"
            item_state = self.get_item_state(self.ms_node, url)
            self.assertTrue("ForRemoval" in item_state)

        # 35. Remove each item type:
        for url in item_urls:
            # 35a. Remove the item at the given URL
            self.execute_cli_remove_cmd(self.ms_node, url)
            # 35b. Check that the state of the test-config item is "ForRemoval"
            item_state = self.get_item_state(self.ms_node, url)
            self.assertTrue("ForRemoval" in item_state)

        # 36. Create a plan
        self.execute_cli_createplan_cmd(self.ms_node)

        # 37. Show plan to check that the correct expected tasks are present
        stdout, stderr, rc = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # 37a. Ensure the URL of each inherited item is in the plan
        for url in url_list:
            # Peer node URLs are too long and are truncated in show command
            if "clusters" in url:
                url = url.split("clusters")[1]
            self.assertTrue(any(url in s for s in stdout))

        # 37b. Ensure the URL of each item type is in the plan
        for url in item_urls:
            self.assertTrue(any(url in s for s in stdout))

        # 37c. Ensure the plan deletes each item type's file
        self.assertTrue(any("ConfigTask to remove file "
                            "/tmp/test-config-1" in s for s in stdout))
        self.assertTrue(any("CallbackTask to remove file "
                            "/tmp/test-callback-1" in s for s in stdout))
        self.assertTrue(any("RemoteExecutionTask to remove file "
                            "/tmp/test-exec-1" in s for s in stdout))

        # 38. Run the plan
        self.execute_cli_runplan_cmd(self.ms_node)

        # 38a. Wait for the plan to complete
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_COMPLETE))

        # 39. Check that all item types are removed
        for url in item_urls:
            # 39a. Run a show command for each item
            _, stderr, rc = self.execute_cli_show_cmd(
                        self.ms_node, url, expect_positive=False)
            self.assertEqual(rc, 1)
            # 39b. Assert that an "InvalidLocationError" error
            #                               is returned from the command
            self.assertTrue(any("InvalidLocationError" in s for s in stderr))

        # 40. Check that all of the created files have been removed
        dir_contents = self.list_dir_contents(self.ms_node, "/tmp")
        for file_name in file_names:
            self.assertTrue(any(file_name not in s for s in dir_contents))

    @attr('all', 'revert', 'system_functionality', 'LITPCommands',
          'LITPCommands_tc05')
    def test_n_fail_start_plan(self):
        """
        Description:
            Create an item with a property to fail a task.
            Run a plan, asserting that it fails.
            Update the property so that the task will pass.
            Run a plan, asserting that it is successful.

        Actions:
            1. Create test-callback item with "def_prop_2" prop set to false.
            2. Inherit test-callback item under MS node.
            3. Create a plan.
            4. Run the plan.
            5. Wait for the plan to fail.
            6. Update the "def_prop_2" property of the item so plan will pass.
            7. Create a plan.
            8. Run the plan.
            9. Wait for the plan to successfully complete.
            10. Remove inherited URL under MS.
            11. Remove item URL.
            12. Create a plan.
            13. Run the plan.
            14. Wait for the plan to complete.
        """
        # 1. Create test-callback item with "def_prop_2" property set to false
        callback_props = {'mand_prop_1': 'test-callback-1',
                                            'def_prop_2': 'false'}
        self._create_item(self.callback_url,
                          self.callback_class, callback_props)

        # 2. Inherit test-callback item under MS node
        inherit_callback_url = "{0}/items/test_callback_{1}".format(
                                    self.model["ms"][0]["url"], self.ms_node)
        self.execute_cli_inherit_cmd(
            self.ms_node, inherit_callback_url, self.callback_url)

        # 3. Create a plan
        self.execute_cli_createplan_cmd(self.ms_node)

        # 4. Run the plan
        self.execute_cli_runplan_cmd(self.ms_node)

        # 5. Wait for the plan to fail
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_FAILED))

        # 6. Update the "def_prop_2" property of the item to true
        prop_name = "def_prop_2"
        prop_value = "true"
        self._update_property(self.callback_url, prop_name, prop_value)

        # 7. Create a plan
        self.execute_cli_createplan_cmd(self.ms_node)

        # 8. Run the plan
        self.execute_cli_runplan_cmd(self.ms_node)

        # 9. Wait for the plan to successfully complete
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_COMPLETE))

        # 10. Remove inherited URL under MS
        self.execute_cli_remove_cmd(self.ms_node, inherit_callback_url)

        # 11. Remove item URL
        self.execute_cli_remove_cmd(self.ms_node, self.callback_url)

        # 12. Create a plan
        self.execute_cli_createplan_cmd(self.ms_node)

        # 13. Run the plan
        self.execute_cli_runplan_cmd(self.ms_node)

        # 14. Wait for the plan to complete
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_COMPLETE))

    @attr('all', 'revert', 'system_functionality', 'LITPCommands',
          'LITPCommands_tc06')
    def test_p_import_update_rpm(self):
        """
        Description:
            Copy the updated LITP compliant RPMs (plugins) to the MS.
            Import and upgrade the RPMs.
            Check that the RPMs upgraded successfully.
            Check that the LITP packages were upgraded successfully.
            Check that a property that was in an item in Version 1 of the RPMs
                    has been removed from the upgraded version from the item.
            Create an item with a property new in Verson 2 and
                    ensure that property is present in the item.
            Update this property and run a plan ensuring
                    the property has successfully been updated.

        Actions:
            1. Copy the RPMs to the MS.
            2. Import the RPMs.
            3. Upgrade the RPMs.
            4. Check that the packages upgraded successfully.
            5. Run "litp version -a" and ensure the packages are present.
            6. Attempt to create a test-remote-execution item with a property
                        that has been removed from the new version of the RPMs.
                a. Ensure there is a PropertyNotAllowedError creating the item.
            7. Create a test-remote-execution item with mandatory properties.
                a. Ensure the new default property is present in item.
            8. Inherit item under MS node.
            9. Create a plan.
            10. Run the plan.
            11. Update the default property of the item.
            12. Create a plan.
            13. Run the plan.
                a. Wait for the plan to complete.
            14. Check that property has been successfully updated to new value.
            15. Remove inherited URL.
            16. Remove item URL.
            17. Create a plan.
            18. Run the plan.
                a. Wait for the plan to complete.
        """
        # Define updated plugin and pluginapi RPM names.
        plugin = "ERIClitptest_plugin_CXP02-1.0.2-202109201225.noarch.rpm"
        pluginapi =\
            "ERIClitptest_pluginapi_CXP01-1.0.2-202109101639.noarch.rpm"

        plugin_folder = "/test_rpms/"
        plugin_path = os.path.dirname(os.path.realpath(__file__))\
                      + plugin_folder + plugin
        plugin_api_path = os.path.dirname(os.path.realpath(__file__))\
                          + plugin_folder + pluginapi

        # 1. Copy the RPMs to the MS.
        self.assertTrue(self.copy_file_to(
            self.ms_node, plugin_path, "/tmp/"))
        self.assertTrue(self.copy_file_to(
            self.ms_node, plugin_api_path, "/tmp/"))

        # 2. Import the RPMs.
        self.execute_cli_import_cmd(self.ms_node, "/tmp/" + plugin, "litp")
        self.execute_cli_import_cmd(self.ms_node, "/tmp/" + pluginapi, "litp")

        # 3. Upgrade the RPMs.
        cmd = self.redhatutils.get_yum_upgrade_cmd(
            [plugin.rsplit('.', 1)[0], pluginapi.rsplit('.', 1)[0]])
        _, stderr, rc = self.run_command(self.ms_node, cmd, su_root=True,
                su_timeout_secs=120)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # 4. Check that the packages upgraded successfully.
        check_installed = [plugin.rsplit('.', 1)[0],
                           pluginapi.rsplit('.', 1)[0]]

        cmd = self.redhatutils.check_pkg_installed(check_installed)
        _, stderr, rc = self.run_command(self.ms_node, cmd)
        self.assertEqual(stderr, [])
        self.assertEqual(rc, 0)

        # 5. Run "litp version -a" and ensure the packages are present.
        cmd = self.cli.get_litp_version_cmd(args='-a')
        stdout, stderr, rc = self.run_command(self.ms_node, cmd)
        self.assertEqual(0, rc)
        self.assertEqual([], stderr)
        self.assertTrue(any(
            "ERIClitptest_plugin: 1.0.2" in s for s in stdout))
        self.assertTrue(any(
            "ERIClitptest_pluginapi: 1.0.2" in s for s in stdout))

        # 6. Attempt to create a test-remote-execution item with a property
        #   that has been removed from the new version of the RPMs.
        props = "mand_prop_1=test-remote-1 opt_prop_1=PropRemoved"

        _, stderr, rc = self.execute_cli_create_cmd(self.ms_node,
            self.remote_url, self.remote_class, props, expect_positive=False)
        # 6a. Ensure there is a PropertyNotAllowedError creating the item.
        self.assertEqual(rc, 1)
        self.assertNotEqual(stderr, [])
        self.assertTrue(any("PropertyNotAllowedError" in s for s in stderr))

        # 7. Create a test-remote-execution item with mandatory properties.
        props = {'mand_prop_1': 'test-remote-1'}
        self._create_item(self.remote_url, self.remote_class, props)

        # 7a. Ensure the new default property is present in item.
        check_props = self.get_props_from_url(
            self.ms_node, self.remote_url, filter_prop="def_prop_2")
        self.assertTrue(check_props != None)

        # 8. Inherit item under MS node.
        inherit_remote_url = "{0}/items/test_config_{1}".format(
                                    self.model["ms"][0]["url"], self.ms_node)
        self.execute_cli_inherit_cmd(
                self.ms_node, inherit_remote_url, self.remote_url)

        # 9. Create a plan.
        self.execute_cli_createplan_cmd(self.ms_node)

        # 10. Run the plan.
        self.execute_cli_runplan_cmd(self.ms_node)

        # 10a. Wait for the plan to complete.
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_COMPLETE))

        # 11. Update the default property of the item.
        prop_name = "def_prop_2"
        prop_value = "NewPropValue"
        self._update_property(self.remote_url, prop_name, prop_value)

        # 12. Create a plan.
        self.execute_cli_createplan_cmd(self.ms_node)

        # 13. Run the plan.
        self.execute_cli_runplan_cmd(self.ms_node)

        # 13a. Wait for the plan to complete.
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_COMPLETE))

        # 14. Check that property has been successfully updated to new value.
        check_props = self.get_props_from_url(
            self.ms_node, self.remote_url, prop_name)
        self.assertEqual(check_props, prop_value)

        # 15. Remove inherited URL.
        self.execute_cli_remove_cmd(self.ms_node, inherit_remote_url)

        # 16. Remove item URL.
        self.execute_cli_remove_cmd(self.ms_node, self.remote_url)

        # 17. Create a plan.
        self.execute_cli_createplan_cmd(self.ms_node)

        # 18. Run the plan.
        self.execute_cli_runplan_cmd(self.ms_node)

        # 18a. Wait for the plan to complete.
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_COMPLETE))
