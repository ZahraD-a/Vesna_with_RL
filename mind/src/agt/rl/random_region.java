package rl;

import jason.asSemantics.*;
import jason.asSyntax.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Internal action to pick a random region from a list.
 * Used to randomize start/goal each episode for robust policy training.
 *
 * Usage in ASL:
 *   rl.random_region([reception, corridor, open_office, outside, common,
 *                     meeting_room, senior_office_1, senior_office_2,
 *                     senior_office_3, boss_office_1, boss_office_2], Region)
 *
 * Returns: Region unified with one randomly selected element from the list.
 */
public class random_region extends DefaultInternalAction {

    private static final Random rng = new Random();

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        if (args.length != 2) {
            throw new Exception("random_region requires 2 arguments: RegionList, OutputRegion");
        }

        ListTerm regionList = (ListTerm) args[0];
        List<Term> regions = new ArrayList<>();
        for (Term t : regionList) {
            regions.add(t);
        }

        if (regions.isEmpty()) {
            throw new Exception("random_region: list is empty");
        }

        Term selected = regions.get(rng.nextInt(regions.size()));
        return un.unifies(args[1], selected);
    }
}
