package vesna.playgrounds.office;

import vesna.SituatedArtifact;
import vesna.WsClient;
import vesna.WsClientMsgHandler;
import java.net.URI;

import org.json.JSONObject;

import static jason.asSyntax.ASSyntax.*;

import cartago.*;

public class CoffeeMachine extends SituatedArtifact {

    private WsClient client;

    public void init( String region, int limit ) {
        super.init( region, limit );
        try {
            client = new WsClient( new URI( "ws://localhost:8090") );
            client.setMsgHandler( new WsClientMsgHandler() {
                @Override
                public void handleMsg( String msg ) {
                    manage_msg( msg );
                }

                @Override
                public void handleError( Exception ex ) {
                    manage_error( ex );
                }
            });
            client.connect();
        } catch( Exception e ){
            e.printStackTrace();
        }
        defineObsProperty( "status", "ready" );
    }

    private void manage_msg( String msg ) {
        log( msg );
        JSONObject log = new JSONObject( msg );
        String sender = log.getString( "sender" );
        String receiver = log.getString( "receiver" );
        String type = log.getString( "type" );
        JSONObject data = log.getJSONObject( "data" );
        switch( type ) {
            case "signal":
                try {
                    handle_event( data );
                } catch ( Exception e ){
                    e.printStackTrace();
                }
                break;

            default:
                log( "Unknown message type: " + type );
        }
    }

    @INTERNAL_OPERATION
    private void handle_event( JSONObject data ) throws Exception{
        String type = data.getString( "type" );
        String status = data.getString( "status" );
        String reason = data.getString( "reason" );
        // Literal perception = createLiteral( type, createLiteral( status ), createLiteral( reason ) );
        if ( type.equals( "interaction" ) && status.equals( "completed" ) ) {
            beginExtSession();
            updateObsProperty( "status", createLiteral( "coffee" ) );
            endExtSession();
            // TODO: make it work without exceptions
            // String cup_name = data.getString( "cup_name" );
            // ArtifactId cup_id = lookupArtifact( cup_name );
            // execLinkedOp( cup_id, "set_content", "espresso" );
        }
    }

    private void manage_error( Exception ex ) {
        log( ex.getMessage() );
    }
    
    @OPERATION
    public void make_coffee( String cup_name ) throws Exception {
        updateObsProperty( "status", "working" );

        JSONObject log = new JSONObject();
        log.put( "sender", get_art_name() );
        log.put( "receiver", "artifact" );
        log.put( "type", "interaction" );
        JSONObject data = new JSONObject();
        data.put( "type", "make_coffee" );
        data.put( "quantity", "espresso" );
        data.put( "cup", cup_name );
        log.put( "data", data );

        client.send( log.toString() );

        // TODO: remove from here and place above
        ArtifactId cup_id = lookupArtifact( cup_name );
        execLinkedOp( cup_id, "set_content", "espresso" );
    }

    @OPERATION
    public void take_cup( ) {
        updateObsProperty( "status", "ready" );
    }

}
