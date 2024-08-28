#!/usr/bin/env python

'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2014
@author:    Maria
@summary:   Integration test to create,remove and update logrotate rules
            Agile: STORY LITPCDS-664
'''

from litp_cli_utils import CLIUtils
import test_constants
from litp_generic_test import GenericTest, attr


class Story18326(GenericTest):

    '''
    Explore use of vapps in Jenkins to run LITP Expansion test cases
    '''

    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        # 1. Call super class setup
        super(Story18326, self).setUp()
        self.test_ms = self.get_management_node_filename()
        self.managed_nodes = self.get_managed_node_filenames()
        self.cli = CLIUtils()

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
        super(Story18326, self).tearDown()

    @attr('all', 'revert', 'vexpand_tc01',
          'expansion', 'expandc1n1toc1n1n2')
    def test_01_p_test_expansion(self):
        """
        Description:
        Tests expansion of a single cluster from 1 to 2 nodes.

        Actions:
          - Run plan to expand c1 by one node.
          - Restore to previous snapshot
          - Create a new snapshot
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")

        #2. Execute the expand script for expanding cluster 1 with node2.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                'expand_cloud_c1_mn2.sh')

        #3. Make edits/additions to the model for the particular test case
        #.
        #.

        #4. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins)

        #5. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)
        self.run_command(self.test_ms, '/usr/bin/mco ping')
        #6. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms, False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc02', 'expandc1n1toc1n1n2n3')
    def test_02_p_test_expansion(self):
        """
        Description:
        Tests expansion of a single cluster from 1 node to 3 nodes.

        Actions:
          - Run plan to expand c1 to 3 nodes.
          - Restore to previous snapshot
          - Create a new snapshot
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")

        #2. Execute the expand script for expanding cluster 1 with node2
        # and node3.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                'expand_cloud_c1_mn2.sh')
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c1_mn3.sh')

        #3. Make edits/additions to the model for the particular test case
        #.
        #.

        #4. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins,
                                add_to_cleanup=False)

        #5. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)
        self.run_command(self.test_ms, '/usr/bin/mco ping')
        #6. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc03', 'expandc1n1toc1n1c2n1')
    def test_03_p_test_expansion(self):
        """
        Description:

        Tests creation of a new cluster with 1 node.

        Actions::
          - Runs a plan to create a new cluster with one node.
          - Restore to previous snapshot
          - Create a new snapshot
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")

        #2. Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments',
                                'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
                'cluster_id=1043'
        self.execute_cli_create_cmd(self.test_ms,
                                cluster_collect + "/c2",
                                'vcs-cluster',
                                 props)

        #3. Execute the expand script for expanding cluster 2 with node2.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                'expand_cloud_c2_mn2.sh')

        #4. Make edits/additions to the model for the particular test case
        #.
        #.

        #5. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins,
                                add_to_cleanup=False)

        #6. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)
        self.run_command(self.test_ms, '/usr/bin/mco ping')
        #7. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc04',
          'expandc1n1toc1n1c2n2n3')
    def test_04_p_test_expansion(self):
        """
        Description:
        Tests creation of a new cluster with 2 nodes.

        Actions:
          - Run a plan to create a new cluster with 2 nodes.
          - Restore to previous snapshot
          - Create a new snapshot
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")

        #2. Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments',
                                'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
                'cluster_id=1043'
        self.execute_cli_create_cmd(self.test_ms,
                                cluster_collect + "/c2",
                                'vcs-cluster',
                                 props, add_to_cleanup=False)

        #3. Execute the expand script for expanding cluster 2 with node2.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                'expand_cloud_c2_mn2.sh')
        self.execute_expand_script(self.test_ms,
                                'expand_cloud_c2_mn3.sh')

        #4. Make edits/additions to the model for the particular test case
        #.
        #.
        #5. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)

        #6. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)

        #7. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc05',
          'expandc1n1toc1n1n2c2n1')
    def test_05_p_test_expansion(self):
        """
        Description:
        Tests creation of a new cluster with 1 node and expansion of existing
        1 node cluster to a 2 node cluster.

        Actions:
          - Run a deployment script which:
               - expands an existing cluster by one node
               - creates a new 1 node cluster
          - Restore to previous snapshot
          - Create a new snapshot
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")

        #2. Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments',
                                'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
                'cluster_id=1043'
        self.execute_cli_create_cmd(self.test_ms,
                                cluster_collect + "/c2",
                                'vcs-cluster',
                                 props, add_to_cleanup=False)

        #3. Execute the expand script for expanding cluster 1 with node2
        # and cluster 2 with node 3.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                'expand_cloud_c1_mn2.sh')
        self.execute_expand_script(self.test_ms,
                                'expand_cloud_c2_mn3.sh')

        #4. Make edits/additions to the model for the particular test case
        #.
        #.

        #5. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)

        #6. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)
        self.run_command(self.test_ms, '/usr/bin/mco ping')
        #7. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc06',
          'expandc1n1toc1n1c2n2c3n3')
    def test_06_p_test_expansion(self):
        """
        Description:
        Tests creation of a two new clusters each with 1 node.

        Then performs the following actions:
           - Run a deployment script which creates 2 new clusters of
             1 node each
          - Create a new snapshot
          - Restore to created snapshot
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")

        #2. Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments',
                                'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
                'cluster_id=1043'
        self.execute_cli_create_cmd(self.test_ms,
                                cluster_collect + "/c2",
                                'vcs-cluster',
                                 props, add_to_cleanup=False)

        #3. Create a new cluster 3
        cluster_collect = self.find(self.test_ms, '/deployments',
                                'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
                'cluster_id=1044'
        self.execute_cli_create_cmd(self.test_ms,
                                cluster_collect + "/c3",
                                'vcs-cluster',
                                 props, add_to_cleanup=False)

        #4. Execute the expand script for expanding cluster 2 with node2
        # and cluster 3 with node 3.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn2.sh')
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c3_mn3.sh')

        #5. Make edits/additions to the model for the particular test case
        #.
        #.

        #6. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)

        #7. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)
        self.run_command(self.test_ms, '/usr/bin/mco ping')
        #8. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc07',
          'expandc1n1toc1n1n2n3n4')
    def test_07_p_test_expansion(self):
        """
        Description:
        Tests creation 3 new nodes in the existing cluster.

        Actions:
          - Run a deployment script which:
               - expands an existing cluster by three nodes
          - Restore to previous snapshot
          - Create a new snapshot
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")
        nodes_to_expand.append("node4")

        #3. Execute the expand script for expanding cluster 1 with node2
        # node 3 and node4
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                    'expand_cloud_c1_mn2.sh',
                    cluster_filename='192.168.0.42_4node.sh')
        self.execute_expand_script(self.test_ms,
                    'expand_cloud_c1_mn3.sh',
                    cluster_filename='192.168.0.42_4node.sh')
        self.execute_expand_script(self.test_ms,
                    'expand_cloud_c1_mn4.sh',
                    cluster_filename='192.168.0.42_4node.sh')

        #4. Make edits/additions to the model for the particular test case
        #.
        #.

        #5. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)

        #6. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)
        self.run_command(self.test_ms, '/usr/bin/mco ping')
        #7. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc08', 'expandc1n1c2n1c3n1')
    def test_08_p_test_expansion(self):
        """
        Description:
        Tests creation of a new clusters each with 3 nodes in the second
        cluster.

        Then performs the following actions:
           - Runs 3 deployment scripts which creates a new cluster of
             3 nodes
          - Create a new snapshot
          - Restore to created snapshot
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")
        nodes_to_expand.append("node4")

        #2. Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments',
                                'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
                'cluster_id=1043'
        self.execute_cli_create_cmd(self.test_ms,
                                cluster_collect + "/c2",
                                'vcs-cluster',
                                 props, add_to_cleanup=False)

        #4. Execute the expand script for expanding cluster 2 with node2
        # node3and node4.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn2.sh',
                                    cluster_filename='192.168.0.42_4node.sh')
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn3.sh',
                                    cluster_filename='192.168.0.42_4node.sh')
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn4.sh',
                                    cluster_filename='192.168.0.42_4node.sh')

        #5. Make edits/additions to the model for the particular test case
        #.
        #.

        #6. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)

        #7. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)
        self.run_command(self.test_ms, '/usr/bin/mco ping')
        #8. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc09', 'expandc1n1c2n1c3n1')
    def test_09_p_test_expansion(self):
        """
        Description:
        Tests creation of a new clusters with 2 nodes in the second
        cluster and one node in the first

        Then performs the following actions:
           - Runs 3 deployment scripts which creates a new clusters of
             2 nodes and adds 1 node to the first
          - Create a new snapshot
          - Restore to created snapshot
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")
        nodes_to_expand.append("node4")

        #2. Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments',
                                'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
                'cluster_id=1043'
        self.execute_cli_create_cmd(self.test_ms,
                                cluster_collect + "/c2",
                                'vcs-cluster',
                                 props, add_to_cleanup=False)

        #4. Execute the expand script for expanding cluster 2 with
        # node3 and node4 and adds node2 to cluster 1
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c1_mn2.sh',
                                    cluster_filename='192.168.0.42_4node.sh')
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn3.sh',
                                    cluster_filename='192.168.0.42_4node.sh')
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn4.sh',
                                    cluster_filename='192.168.0.42_4node.sh')

        #5. Make edits/additions to the model for the particular test case
        #.
        #.

        #6. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)

        #7. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)
        self.run_command(self.test_ms, '/usr/bin/mco ping')
        #8. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc10',
          'expandc1n1toc1n1n2n3c2n4')
    def test_10_p_test_expansion(self):
        """
        Description:
        Tests expansion of a deployment.
        """
        # 1. We create a list of the nodes we will be adding. Note if using a
        # script name which contains 'mn2' you should use node2. If using a
        # script with contains 'mn3' you should add 'node3' and 'node4' for
        # 'mn4'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")
        nodes_to_expand.append("node4")

        # 2. Execute the expand script for expanding cluster 1 with node2 and
        # node3.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c1_mn2.sh',
                                   cluster_filename='192.168.0.42_4node.sh')
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c1_mn3.sh',
                                   cluster_filename='192.168.0.42_4node.sh')

        # 3. Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments',
                                    'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' + \
                'cluster_id=1043'
        self.execute_cli_create_cmd(self.test_ms,
                                    cluster_collect + "/c2",
                                    'vcs-cluster',
                                    props)

        # 4. Execute the expand script for expanding cluster 2 with node4.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn4.sh',
                                   cluster_filename='192.168.0.42_4node.sh')

        # 5. Make edits/additions to the model for the particular test case
        # .
        # .
        # 6. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins,
                                add_to_cleanup=False)

        # 7. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)

        # 8. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('all', 'revert', 'expansion', 'vexpand_tc11',
          'expandc1n1toc1n1c2n2c3n3c4n4')
    def test_11_p_test_expansion(self):
        """
        Description:
        Tests expansion of a single cluster from 1 node, to 4 clusters, each
         with 1 node.
        """
        # 1. We create a list of the nodes we will be adding.
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")
        nodes_to_expand.append("node4")

        # 2. Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments',
                                    'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' + \
                'cluster_id=1043'
        self.execute_cli_create_cmd(self.test_ms,
                                    cluster_collect + "/c2",
                                    'vcs-cluster',
                                    props)

        # 3. Execute the expand script for expanding cluster 2 with node2.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c2_mn2.sh',
                                   cluster_filename='192.168.0.42_4node.sh')

        # 4. Create a new cluster 3
        cluster_collect = self.find(self.test_ms, '/deployments',
                                    'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' + \
                'cluster_id=1044'
        self.execute_cli_create_cmd(self.test_ms,
                                    cluster_collect + "/c3",
                                    'vcs-cluster',
                                    props)

        # 5. Execute the expand script for expanding cluster 3 with node3.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c3_mn3.sh',
                                   cluster_filename='192.168.0.42_4node.sh')

        # 6. Create a new cluster 4
        cluster_collect = self.find(self.test_ms, '/deployments',
                                    'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' + \
                'cluster_id=1045'
        self.execute_cli_create_cmd(self.test_ms,
                                    cluster_collect + "/c4",
                                    'vcs-cluster',
                                    props)

        # 7. Execute the expand script for expanding cluster 4 with node4.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                   'expand_cloud_c4_mn4.sh',
                                   cluster_filename='192.168.0.42_4node.sh')

        # 8. Make edits/additions to the model for the particular test case
        # .

        # 9. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_COMPLETE,
                                timeout_mins,
                                add_to_cleanup=False)

        # 10. If the expansion has suceeded we restore_snapshot to bring us
        # back to a one node state again. Note we set the poweroff_nodes value
        # as expanded nodes should be powered off before restoring back.
        self.execute_and_wait_restore_snapshot(self.test_ms,
                                               poweroff_nodes=nodes_to_expand)

        # 11. Create a new snapshot for the next test to have a restore_point
        self.execute_and_wait_createsnapshot(self.test_ms,
                                             add_to_cleanup=False)

    @attr('revert', 'expansion', 'vexpand_tc012', 'resume')
    def test_12_p_test_expansion_resume(self):
        """
        Description:
        Run expand plan we expect to fail due to sfs being shutdown.
        """
        #1. We create a list of the nodes we will be adding. Note if using a
        #script name which contains 'mn2' you should use node2. If using a
        #script with contains 'mn3' you should add 'node3'
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")

        #2. Create a new cluster 2
        cluster_collect = self.find(self.test_ms, '/deployments',
                                'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
                'cluster_id=1043'
        self.execute_cli_create_cmd(self.test_ms,
                                cluster_collect + "/c2",
                                'vcs-cluster',
                                 props, add_to_cleanup=False)

        #3. Execute the expand script for expanding cluster 2 with node2.
        # Note this does not create or run the plan.
        self.execute_expand_script(self.test_ms,
                                'expand_cloud_c2_mn2.sh')
        self.execute_expand_script(self.test_ms,
                                'expand_cloud_c2_mn3.sh')

        sfs_node = self.get_sfs_node_filenames()[0]
        self.run_command(sfs_node, "/sbin/shutdown -h now")

        #4. Make edits/additions to the model for the particular test case
        #.
        #.
        #5. Run plan and wait for it to complete the expansion.
        timeout_mins = 60
        self.run_and_check_plan(self.test_ms,
                                test_constants.PLAN_FAILED,
                                timeout_mins, add_to_cleanup=False)
