package jmri.jmrix.loconet;

import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestSuite;

/**
 * Generated by JBuilder
 * <p>
 * Title: LnTrafficControllerTest </p>
 * <p>
 * Description: </p>
 * <p>
 * Copyright: Copyright (c) 2002</p>
 *
 * @author Bob Jacobsen
 * @version $Id: LnTrafficControllerTest.java 27828 2014-12-11 22:46:11Z
 * jacobsen $
 */
public class LnTrafficControllerTest extends TestCase {

    public LnTrafficControllerTest(String s) {
        super(s);
    }

    public void testNull() {
        // just to make JUnit feel better
    }

    // Main entry point
    static public void main(String[] args) {
        String[] testCaseName = {LnTrafficControllerTest.class.getName()};
        junit.textui.TestRunner.main(testCaseName);
    }

    // test suite from all defined tests
    public static Test suite() {
        TestSuite suite = new TestSuite(LnTrafficControllerTest.class);
        return suite;
    }

    // The minimal setup for log4J
    protected void setUp() {
        apps.tests.Log4JFixture.setUp();
    }

    protected void tearDown() {
        apps.tests.Log4JFixture.tearDown();
    }

}
