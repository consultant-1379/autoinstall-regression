package com.ericsson.nms.litp.taf.test.autoinstall_regression.cases;
//package com.ericsson.nms.litp.taf.test.cases;

import java.util.List;
import java.util.Map;
import java.io.*;
import org.apache.log4j.Logger;
import org.testng.SkipException;
import org.testng.annotations.Test;
import com.ericsson.cifwk.taf.*;
import com.ericsson.cifwk.taf.annotations.*;
import com.ericsson.cifwk.taf.tools.cli.TimeoutException;

import com.ericsson.nms.litp.taf.operators.PythonTestRunner;
import com.ericsson.nms.litp.taf.operators.Error;

import javax.inject.Inject;


public class LITPRegressionTestRunner extends TorTestCaseHelper {

    Logger logger = Logger.getLogger(LITPRegressionTestRunner.class);
    
    @Inject
    private PythonTestRunner pythonTestRunnerOperator;

    /**
     * @throws TimeoutException
     * @DESCRIPTION Run python test scripts for ERIClitpcli package
     * @PRE Connection to SUT
     * @PRIORITY HIGH
     */
    @TestId(id = "CXP9031870-1", title = "Run python test cases for Regression Suites")
    @Test(groups={"ACCEPTANCE", "CDB_REGRESSION"})
    public void runERIClitpRegressionTests() {
    	
        pythonTestRunnerOperator.initialise();

        assertEquals(0, pythonTestRunnerOperator.execute());
    }

    /**
     * @DESCRIPTION Verify that the Python xml reports can be consumed and reported
     * @PRE Execution of test {@link #runERIClitpcliTests()}
     * @PRIORITY HIGH
     * @param className
     * @param name
     * @param failures
     */
    @TestId(id = "CXP9031870-2", title = "Parse xml outputs from python tests")
    @DataDriven(name = "surefire-reports")
    @Test(groups={"ACCEPTANCE"})
    public void parseNosetestsReports(@Input("classname") String className, @Input("name") String name, 
            @Input("failures") List<Map<String, String>> failures, @Input("errors") List<Map<String, String>> errors,
            @Input("skipped") List<Map<String, Object>> skipped){
        logger.debug("TestCase:");
        logger.debug("    classname:" + className);
        logger.debug("    name:" + name);
        setTestcase(className + ":" + name, "");
        setTestInfo(name);
        for (Map<String, String> failure : failures) {
            fail(failure.get("type") + failure.get("message") + failure.get("text"));
        }
        for (Map<String, String> error : errors) {
            throw new Error(error.get("type"), error.get("message"), error.get("text"));
        }
        for (Map<String, Object> skip : skipped) {
            int type = (int) skip.get("type");
            if(type > 0){
                throw new SkipException("Number of tests to be skipped is: " + type);
            }
        }
    }
} 
