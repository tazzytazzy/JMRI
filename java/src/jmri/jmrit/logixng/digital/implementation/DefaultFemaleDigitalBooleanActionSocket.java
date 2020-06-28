package jmri.jmrit.logixng.digital.implementation;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import jmri.InstanceManager;
import jmri.JmriException;
import jmri.jmrit.logixng.*;
import jmri.jmrit.logixng.implementation.AbstractFemaleSocket;

/**
 * Default implementation of the Female Digital Boolean Action socket
 */
public final class DefaultFemaleDigitalBooleanActionSocket
        extends AbstractFemaleSocket
        implements FemaleDigitalBooleanActionSocket {


    public DefaultFemaleDigitalBooleanActionSocket(Base parent, FemaleSocketListener listener, String name) {
        super(parent, listener, name);
    }
    
    @Override
    public boolean isCompatible(MaleSocket socket) {
        return socket instanceof MaleDigitalBooleanActionSocket;
    }
    
    @Override
    public void execute(boolean hasChangedToTrue) throws JmriException {
        if (isConnected()) {
            ((MaleDigitalBooleanActionSocket)getConnectedSocket())
                    .execute(hasChangedToTrue);
        }
    }

    @Override
    public String getShortDescription(Locale locale) {
        return Bundle.getMessage(locale, "DefaultFemaleDigitalActionWithChangeSocket_Short");
    }

    @Override
    public String getLongDescription(Locale locale) {
        return Bundle.getMessage(locale, "DefaultFemaleDigitalActionWithChangeSocket_Long", getName());
    }

    @Override
    public Map<Category, List<Class<? extends Base>>> getConnectableClasses() {
        return InstanceManager.getDefault(DigitalBooleanActionManager.class).getActionClasses();
    }

    /** {@inheritDoc} */
    @Override
    public void disposeMe() {
        // Do nothing
    }

}
