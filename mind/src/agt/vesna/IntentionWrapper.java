package vesna;

import jason.asSemantics.Intention;
import jason.asSyntax.Pred;

public class IntentionWrapper implements TemperSelectable {

    private final Intention intention;

    public IntentionWrapper( Intention intention ) {
        this.intention = intention;
    }

    @Override
    public Pred getLabel() {
        return intention.peek().getPlan().getLabel();
    }

    public Intention getIntention() {
        return intention;
    }

}