"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:    April 2017
@authors:  Eimhin Smyth
"""

import re
from litp_generic_test import GenericTest, attr


class HardwarewConnectionChecker(GenericTest):
    """
    This is more of a util than a test, it checks which addresses on
    each node are reachable and which are not
    """
    def setUp(self):
        super(HardwarewConnectionChecker, self).setUp()
        self.all_nodes = [self.get_management_node_filenames()[0]]
        for node in self.get_managed_node_filenames():
            self.all_nodes.append(node)

    def tearDown(self):
        super(HardwarewConnectionChecker, self).tearDown()

    def get_address_status(self, node, local=True):
        """
            Description:
                Gets a list of all addresses on a node and checks
                which are reachable, which are not
            Args:
                node(str):The node which addresses being checked for
            Kwargs:
                local(bool): If this is true, ping will be run from
                             local machine, otherwise ping will be
                             run from nodde
        """
        self.log("info", "###############################")
        self.log("info", "Checking addresses on " + node)
        self.log("info", "###############################")
        #gets a list of addresses on the ndoe with ifconfig
        std_out, _, _ = self.run_command(node, "/sbin/ifconfig -a",
                                         su_root=True)
        last_line = ""
        #this dict will hold which ips are reachable and which are not
        reachable_dict = {"True": [], "False": []}
        #this dict will map names to ip addresses
        ip_dict = {}
        #go through the results of ifconfig
        for line in std_out:
            #if a nic has an inet address, get that address
            if "inet addr:" in line:
                match = re.search("(?:inet addr:)(\\d+\\.\\d+\\.\\d+\\.\\d+)",
                                  line)
                #add to dict wih nic name as key and ip as value
                ip_dict[last_line[:10].strip()] = match.group(1)
            #we need to remember the previous line as it contains the
            #nic name while the current line contains the ip address
            last_line = line
        #for each address found, ping it. Record whether it's
        #reachable in our reachable_dict
        for key in ip_dict:
            if local:
                res = self.wait_for_ping(ip_dict[key], ping_success=True,
                                         timeout_mins=0.01)
            else:
                res = self.wait_for_ping(ip_dict[key], ping_success=True,
                                         timeout_mins=0.01, node=node)
            reachable_dict[str(res)].append((key, ip_dict[key]))
        return reachable_dict

    def log_results(self, node, results, local_results):
        """
        Description:
            Logs results
        Args:
            node(str): The node which addresses being logged belong to
            results(dict): A dictionary tracking addresses which are
                           reachable from the node and which are not
            local_results(dict): A dictionary that tracks addresses
                                 which are reachable from the gateway
                                 and which are not
        """
        #This logs addresses that are reachable
        #from the gateway
        self.log("info", "The following addresses on " + node +
                 " are reachable from the gateway:")
        for result in results["True"]:
            print result[0] + "\t\t" + result[1]
        #This logs addresses that are unreachable
        #from the gateway
        self.log("info", "The following addresses on " + node +
                 " are unreachable from the gateway:")
        for result in results["False"]:
            print result[0] + "\t\t" + result[1]
        #This logs addresses on a node that are
        #reachable from that node
        self.log("info", "The following addresses on " + node +
                 " are reachable from " + node)
        for result in local_results["True"]:
            print result[0] + "\t\t" + result[1]
        #This logs addresses on a node that are
        #unreachable from that node
        self.log("info", "The following addresses on " + node +
                 " are unreachable from " + node + ":")
        for result in local_results["False"]:
            print result[0] + "\t\t" + result[1]

    @attr("interface_check", "revert")
    def test_01_p_get_nic_list(self):
        """
        Description: Checks which addresses on each node are reachable
                     and which are not
        """
        results_dict = {}
        #go through each node
        for node in self.all_nodes:
            #this dict maps a tuple of results(results, local_results)
            #to a node
            results_dict[node] = (self.get_address_status(node, False),
                                  self.get_address_status(node))
        self.log("info", "###############")
        self.log("info", "LOGGING RESULTS")
        self.log("info", "###############")
        #for each node, log results
        for key in results_dict:
            self.log_results(key, results_dict[key][0], results_dict[key][1])
