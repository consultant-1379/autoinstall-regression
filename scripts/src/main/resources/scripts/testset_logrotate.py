"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    Bryan O'Neill
"""

from litp_generic_test import GenericTest, attr
import test_constants


class Logrotate(GenericTest):
    """
    Test the 'logrotate-rule' LITP item type.
    """

    def setUp(self):
        """ Setup Variables for every test """

        super(Logrotate, self).setUp()

        self.model = self.get_model_names_and_urls()
        self.ms_node = self.model["ms"][0]["name"]

    def teardown(self):
        """ Teardown run after every test """

        super(Logrotate, self).setUp()

    @staticmethod
    def string_format(new_string):
        """Function to remove all whitespaces and newlines from a string"""
        # remove '\n' from string
        new_string = new_string.replace('\\n', '')
        new_string = new_string.replace('\n', '')
        # remove whitespaces from strings
        new_string = new_string.replace(" ", "")
        return new_string

    def check_logrotate_script_properties(self, prop, value, rule_config):
        """"
        Function to handle checking of scripts in logrotate config:
            postrotate
            prerotate
            firstaction
            lastaction
        """
        idx = rule_config.index(prop)
        config = rule_config[(idx + 1):]
        endscript_idx = config.index("endscript")

        if endscript_idx == 1:
            # there is only 1 line between the script initiator and the
            # endscript identifier so the LITP string can easily be compared
            self.assertEqual(value, rule_config[idx + 1])

        else:
            # in this case the script is over multiple lines. Lines need to be
            # concatenated. Remove spaces from LITP and logrotate config. As
            # the config is on multiple lines there is more than likely '\n'
            # values in the LITP config so removal of '\n' is also required

            # take a slice of the logrotate config that holds only the lines
            # betwwen the script initiator and endscript.
            config = config[: endscript_idx]

            # concatenate lines.
            script_string = "".join(config)

            script_string = self.string_format(script_string)
            value = self.string_format(value)

            self.assertEqual(value, script_string)

    @attr('all', 'revert', 'system_check', 'logrotate', 'logrotate_tc01')
    def test_01_p_logrotate_rules_implemented(self):
        """
        Description:
            Test the 'logrotate-rule' LITP item type.
            Verify that any logrotate rules in the LITP model are configured on
            the corresponding node/ms.
        Actions:
            1. Create a list of all nodes and MS to iterate over.
            2. For each node:
                a. Get logrotate rules
                b. For each rule:
                    b1. Get rule properties
                    b2. Check rule exists on node
                    b3. Get rule config from node
                    b4. Verify config from node matches model properties
        """
        # 1. Create a list of node items to iterate over. This list includes
        #    the MS as we need to check logrotate rules on it too.
        all_nodes = self.model["nodes"][:]
        all_nodes.extend(self.model["ms"][:])

        for node in all_nodes:
            # a. Get logrotate rules
            rules = self.find(self.ms_node, node["url"], "logrotate-rule",
                              assert_not_empty=False)

            for rule in rules:
                # b1. Get rule properties.
                props = self.get_props_from_url(self.ms_node, rule)

                rule_path = "{0}{1}".format(test_constants.LOGROTATE_PATH,
                                            props["name"])
                # if the rule applys to multiple paths remove comma and replace
                # with space
                rule_path = rule_path.replace(",", " ")

                # b2. Check rule exists on node.
                self.assertTrue(self.remote_path_exists(node["name"],
                                                        rule_path,
                                                        su_root=True))

                # b3. Get rule config from node.
                self.log("info", "Getting config for rule {0} from {1}"
                         .format(props["name"], node["name"]))
                rule_config = self.get_file_contents(node["name"], rule_path,
                                                     su_root=True)

                # b4. Verify config from node matches model properties.

                # remove useless lines from config
                # if the rule applies to multiple logs then the comma separated
                # line needs to be changed to whitespace separated
                index = rule_config.index("{0} {{"
                                          .format(props["path"]
                                                  .replace(",", " ")))
                rule_config = rule_config[(index + 1): -1]

                # remove name and path properties from model properties as they
                # will not be in the config from the node.
                del props["name"]
                del props["path"]

                # dict of intervals to convert from LITP to logrotate values.
                # needed only for the rotate_every property.
                interval = {"day": "daily", "week": "weekly",
                            "month": "monthly", "year": "yearly"}
                scripts = ["prerotate", "postrotate",
                           "firstaction", "lastaction"]

                for prop in props:
                    # If the property is a boolean then in the rule config we
                    # need to match e.g. create or nocreate for true or false
                    # respectively.

                    if props[prop].lower() == "true":
                        self.assertTrue(prop in rule_config)
                        continue

                    if props[prop].lower() == "false":
                        if prop == "ifempty":
                            self.assertTrue(("not" + prop) in rule_config)
                            continue

                        if prop == "mailfirst" or prop == "maillast":
                            if props[prop] == "false":
                                self.assertTrue(prop not in rule_config)
                                continue

                            self.assertTrue(prop in rule_config)
                            continue

                        self.assertTrue(("no" + prop) in rule_config)
                        continue

                    if prop == "rotate_every":
                        self.assertTrue(interval[props[prop]] in rule_config)
                        continue

                    if prop in scripts:
                        # this option is a script and will appear on multiple
                        # lines. Use function to handle.
                        self.check_logrotate_script_properties(prop,
                                                               props[prop],
                                                               rule_config)
                        continue

                    # property is not a bool, a script or rotate_every so
                    # must have a value.
                    self.assertTrue("{0} {1}".format(prop, props[prop])
                                    in rule_config)
