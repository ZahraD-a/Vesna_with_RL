package vesna;

import jason.JasonException;
import jason.architecture.AgArch;
import jason.asSemantics.*;
import jason.asSyntax.*;
import jason.runtime.RuntimeServicesFactory;
import jason.mas2j.ClassParameters;
import jason.bb.BeliefBase;
import jason.bb.DefaultBeliefBase;
import jason.runtime.Settings;
import jason.NoValueException;

import static jason.asSyntax.ASSyntax.*;

import java.net.URI;

import org.gradle.internal.impldep.org.apache.commons.lang.StringUtils;
import org.json.JSONObject;

import java.util.HashMap;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.Random;
import java.util.Queue;
import java.util.Set;
import java.util.HashSet;
import java.util.Iterator;
import java.util.stream.Collectors;

import java.util.logging.Logger;

import javax.validation.OverridesAttribute;

/**
 * <p>
 * 	VesnaAgent class extends the Agent class making the agent embodied;
 * 	It connects to the body using a WebSocket connection;
 * </p>
 * <p>
 * 	It can use four parameters:
 * 	<ul>
 * 		<li> {@code address( ADDRESS )} and {@code port( PORT )} that describe the address and port of the WebSocket server;</li>
 * 		<li> {@code temper( [ LIST OF PROPENSIONS ] )} and {@code strategy( most_similar | random )} for the plan temper choice.</li>
 * 		<li> {@code strategy( most_similar | random )} for the plan temper choice.</li>
 * 	</ul>
 * <p>
 * In order to use it you should add to your .jcm:
 * <pre>
 * agent alice:alice.asl {
 * 	ag-class: 		vesna.VesnaAgent
 * 	address: 		localhost
 * 	port: 			8080
 * 	temper:			propensions([ ... ])
 * 	strategy: 		random
 * }
 * </pre>
 * @author Andrea Gatti
 */
public class VesnaAgent extends Agent{

	// GLOBAL VARIABLES
	/** WebSocket Client that connects with the body */
	private WsClient client;
	// // private String myName;
	/** The temper of the agent */
	private Temper temper;
	// // private Random dice = new Random();
	/** The logger necessary to print on the JaCaMo log */
	protected transient Logger logger;

	/** Initialize the agent with body and temper
	 * <p>
	 * Override initAg method in order to:
	 * <ul>
	 *	<li> connect to the body if needed; </li>
	 *	<li> initialize the temper if needed. </li>
	 * </ul>
	 */
	public void initAg() {

		super.initAg();

		// Initialize the global variables
		// // myName = getTS().getAgArch().getAgName();
		Settings stts = getTS().getSettings();
		String temperStr 	= stts.getUserParameter( "temper" );
		String strategy 	= stts.getUserParameter( "strategy" );
		String address 		= stts.getUserParameter( "address" );
		int port 			= Integer.parseInt( stts.getUserParameter( "port" ) );
		logger = getTS().getLogger();

		if ( temperStr != null )
			// Initialize the agent temper and strategy
			temper = new Temper( temperStr, strategy );

		logger.info( "Body is at " + address + " : " + port );

		initBody( address, port );

	}

	/**
	 * <p>
		* Initialize the Body connection through WebSocket.
		* @param	address	the address where the body is located
		* @param	port	the port where the body is listening
	 */
	private void initBody( String address, int port ) {

		// Initialize the WebSocket client
		try {
			URI bodyAddress = new URI( "ws://" + address + ":" + port );
			client = new WsClient( bodyAddress );
		} catch( Exception e ){
			stop( e.getMessage() );
		}

		// Connect the two handle functions to the client object
		client.setMsgHandler( new WsClientMsgHandler() {
			@Override
			public void handleMsg( String msg ) {
				vesnaHandleMsg( msg );
			}

			@Override
			public void handleError( Exception ex ) {
				vesnaHandleError( ex );
			}
		}  );

		// Connect the body
		try {
			client.connect();
		} catch( Exception e ){
			stop( e.getMessage() );
		}

	}

	/** Performs a body action in the environment
	 * @param action The action to perform formatted into a JSON string
	*/
	public void perform( String action ) {
		client.send( action );
	}

	/** Signals the mind about a perception
	 * @param perception The perception to signal formatted as Jason Literal
	*/
	private void sense( Literal perception ) {
		try {
			Message signal = new Message( "signal", getTS().getAgArch().getAgName(), getTS().getAgArch().getAgName() , perception );
			getTS().getAgArch().sendMsg( signal );
		} catch ( Exception e ) {
			e.printStackTrace();
		}
	}

	/** Takes all the data from an event and senses a perception
	 * @param event The event to handle formatted as JSON object:
		* <pre>
		 * {
		 *   "type": "event_type",
		 *   "status": "event_status",
		 *   "reason": "event_reason"
		 * }
		* </pre>
	* It will <i>sense</i> a literal formatted as {@code event_type( event_status, event_reason )}.
	*/
	private void handleEvent( JSONObject event ) {
		String event_type = event.getString( "type" );
		String event_status = event.getString( "status" );
		String event_reason = event.getString( "reason" );
		Literal perception = createLiteral( event_type, createLiteral( event_status ), createLiteral( event_reason ) );
		sense(perception);
	}

	/**
	* Takes all the data from a sight and adds a belief
	* @param sight The sight to handle formatted as JSON object:
		* <pre>
		 * {
		 *   "sight": "object",
		 *   "id": 1234567890
		 * }
		* </pre>
		* It will <i>add a belief</i> formatted as {@code sight( object, id )}.
	*/
	private void handleSight( JSONObject sight ) {
		String object = sight.getString( "sight" );
		long id = sight.getLong( "id" );
		Literal sight_belief = createLiteral( "sight", createLiteral( object ), createNumber( id ) );
		try{
			addBel( sight_belief );
		} catch ( Exception e ) {
			e.printStackTrace();
		}
	}

	/** Handles incoming messages from the body.
	* Available types are: signal, sight.
	* @param msg The message received formatted as JSON string:
	* <pre>
	 * {
	 *   "sender": "body",
	 *   "receiver": "agent_name",
	 *   "type": "signal | sight",
	 *   "data": { ... }
	 * }
	 * </pre>
	*/
	public void vesnaHandleMsg( String msg ) {
		System.out.println( "Received message: " + msg );
		JSONObject log = new JSONObject( msg );
		String sender = log.getString( "sender" );
		String receiver = log.getString( "receiver" );
		String type = log.getString( "type" );
		JSONObject data = log.getJSONObject( "data" );
		switch( type ){
			case "signal":
				handleEvent( data );
				break;
			case "sight":
				handleSight( data );
				break;
			default:
				logger.warning( "Unknown message type: " + type );
		}
	}

	/** Stops the agent: prints a message and kills the agent
	 * @param reason The reason why the agent is stopping
	 */
	private void stop( String reason ) {
		logger.severe( reason );
		kill_agent();
	}

	/** Handles a connection error: prints a message and kills the agent
	 * @param ex The exception raised
	 */
	public void vesnaHandleError( Exception ex ){
		logger.severe( ex.getMessage() );
		kill_agent();
	}

	/** Kills the agent
	 * <p>
	 * It calls the internal actions to drop all desires, intentions and events and then kill the agent;
	 * This is necessary to avoid the agent to keep running after the kill_agent call ( that otherwise is simply enqueued ).
	 * </p>
	 */
	private void kill_agent() {
		logger.severe( "Killing agent" );
		try {
			InternalAction drop_all_desires = getIA( ".drop_all_desires" );
			InternalAction drop_all_intentions = getIA( ".drop_all_intentions" );
			InternalAction drop_all_events = getIA( ".drop_all_events" );
			InternalAction action = getIA( ".kill_agent" );

			drop_all_desires.execute( getTS(), new Unifier(), new Term[] {} );
			drop_all_intentions.execute( getTS(), new Unifier(), new Term[] {} );
			drop_all_events.execute( getTS(), new Unifier(), new Term[] {} );
			action.execute( getTS(), new Unifier(), new Term[] { createString( getTS().getAgArch().getAgName() ) } );
		} catch ( Exception e ) {
			e.printStackTrace();
		}
	}

	/** Overrides the selectOption in order to consider Temper if needed
	 * <p>
	 * If there is only one option or the options are without temper it goes with the default selection;
	 * Otherwise it calls the temper select method.
	 * </p>
	 * @param options The list of options to choose from
	 * @return The selected option
	 * @see vesna.Temper#select(List) Temper.select(List)
	 */
	public Option selectOption( List<Option> options ) {

		// If there is only one options or the options are without temper go with the default
		if ( options.size() == 1 || !areOptionsWithTemper( options ) )
			return super.selectOption( options );

		// Wrap the options inside an object Temper Selectable
		List<OptionWrapper> wrappedOptions = options.stream()
			.map( OptionWrapper::new )
			.collect( Collectors.toList() );

		// Select with temper
		try {
			return temper.select( wrappedOptions ).getOption();
		} catch ( NoValueException nve ) {
			stop( nve.getMessage() );
		}
		return null;
	}

	/** Overrides the selectIntention in order to consider Temper if added
	 * <p>
	 * If there is only one intention or the intentions are without temper it goes with the default selection;
	 * Otherwise it calls the temper select method.
	 * </p>
	 * @param intentions The queue of intentions to choose from
	 * @return The selected intention
	 * @see vesna.Temper#select(List) Temper.select(List)
	 */
	public Intention selectIntention( Queue<Intention> intentions ) {

		// logger.info( "I have " + intentions.size() + " intentions" );

		// If there is only one intention or the intentions are without temper go with the default
		if ( intentions.size() == 1 || !areIntentionsWithTemper(intentions ) )
			return super.selectIntention( intentions );

		// Wrap the intentions inside an object Temper Selectable
		List<IntentionWrapper> wrappedIntentions = new ArrayList<>( intentions ).stream()
			.map( IntentionWrapper::new )
			.collect( Collectors.toList() );

		// Select with temper and remove the Intention from the queue
		try {
			Intention selected = temper.select( wrappedIntentions ).getIntention();
			Iterator<Intention> it = intentions.iterator();
			while( it.hasNext() ) {
				if ( it.next() == selected ) {
					it.remove();
					break;
				}
			}
			return selected;
		} catch ( NoValueException nve ) {
			stop( nve.getMessage() );
		}
		return null;
	}

	/** Check if there is at least one option with temper annotation
	 * @param options The list of options to check
	 * @return true if at least one option has temper annotation, false otherwise
	 */
	private boolean areOptionsWithTemper( List<Option> options ) {
		Literal propension = createLiteral( "temper", new VarTerm( "X" ) );
		for ( Option option : options ) {
			Plan p = option.getPlan();
			Pred l = p.getLabel();
			if ( l.hasAnnot() ) {
				for ( Term t : l.getAnnots() )
					if ( new Unifier().unifies( propension, t ) )
						return true;
			}
		}
		return false;
	}

	/** Check if there is at least one intention with temper annotation
	 * @param intentions The queue of intentions to check
	 * @return true if at least one intention has temper annotation, false otherwise
	 */
	private boolean areIntentionsWithTemper( Queue<Intention> intentions ) {
		Literal propension = createLiteral( "propensions", new VarTerm( "X" ) );
		for ( Intention intention : intentions ) {
			Plan p = intention.peek().getPlan();
			Pred l = p.getLabel();
			if ( l.hasAnnot() ) {
				for ( Term t : l.getAnnots() )
					if ( new Unifier().unifies( propension, t ) )
						return true;
			}
		}
		return false;
	}

}
