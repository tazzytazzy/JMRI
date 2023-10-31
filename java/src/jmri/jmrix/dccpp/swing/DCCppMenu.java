package jmri.jmrix.dccpp.swing;

import java.util.ResourceBundle;
import javax.swing.JMenu;

/**
 * Create a menu containing the DCC++ specific tools.
 *
 * @author Paul Bender Copyright 2003,2010
 * @author Mark Underwood Copyright 2015
 *
 * Based on XNetMenu by Paul Bender
 */
public class DCCppMenu extends JMenu {


    public DCCppMenu(String name, jmri.jmrix.dccpp.DCCppSystemConnectionMemo memo) {
        this(memo);
        setText(name);
    }

    public DCCppMenu(jmri.jmrix.dccpp.DCCppSystemConnectionMemo memo) {

        super();
        ResourceBundle rb = ResourceBundle.getBundle("jmri.jmrix.dccpp.swing.DCCppSwingBundle");

        if (memo != null) {
            setText(memo.getUserName());
        } else {
            setText(rb.getString("MenuDCC++"));
        }

        if (memo != null) {
            add(new jmri.jmrix.dccpp.swing.mon.DCCppMonAction(rb.getString("DCCppMonFrameTitle"), memo));
            add(new jmri.jmrix.dccpp.swing.lcd.DisplayAction(rb.getString("MenuItemDisplay"), memo));
            add(new jmri.jmrix.dccpp.swing.packetgen.PacketGenAction(rb.getString("MenuItemSendDCCppCommand"), memo));
            add(new jmri.jmrix.dccpp.swing.ConfigBaseStationAction(rb.getString("MenuItemConfigBaseStation"), memo));
        }
        add(new jmri.jmrit.swing.meter.MeterAction());
        add(new jmri.jmrix.dccpp.swing.DCCppRosterExportAction(rb.getString("DCCppRosterExportTitle")));
        add(new javax.swing.JSeparator());
        add(new jmri.jmrix.dccpp.dccppovertcp.ServerAction(rb.getString("MenuItemDCCppOverTCPServer")));
    }

}
