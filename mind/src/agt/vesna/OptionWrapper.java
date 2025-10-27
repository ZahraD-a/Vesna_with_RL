package vesna;

import jason.asSemantics.Option;
import jason.asSyntax.Pred;

public class OptionWrapper implements TemperSelectable {

    private final Option option;

    public OptionWrapper( Option option ) {
        this.option = option;
    }

    @Override
    public Pred getLabel() {
        return option.getPlan().getLabel();
    }

    public Option getOption() {
        return option;
    }

}