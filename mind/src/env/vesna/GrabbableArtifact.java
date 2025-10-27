package vesna;

import cartago.Artifact;
import cartago.OPERATION;

import jason.infra.local.LocalAgArch;
import jason.infra.local.RunLocalMAS;

import static jason.asSyntax.ASSyntax.*;

import org.json.JSONObject;

public class GrabbableArtifact extends Artifact {

    private String owner;
    private String region;
    private String art_name;

    void init( String region ) {
        this.region = region;
        this.owner = null;
        this.art_name = getId().getName();
    }


    @OPERATION
    public void grab( String ag_region ) throws Exception{

        if ( ! ag_region.equals( this.region ) ) {
            log( "You cannot grab this artifact: it is in another region!" );
            failed( "You cannot grab this artifact: it is in another region!" );
        }

        if ( this.owner != null ){
            log( "You cannot grab this artifact: it has already an owner!" );
            failed( "You cannot grab this artifact: it has already an owner!" );
        }

        String ag_name = getCurrentOpAgentId().getAgentName();
        this.owner = ag_name;

        log( ag_name + " has grabbed " + this.art_name );

        JSONObject action = new JSONObject();
        action.put( "sender", ag_name );
        action.put( "receiver", "body" );
        action.put( "type", "interact" );
        JSONObject data = new JSONObject();
        data.put( "type", "grab" );
        data.put( "art_name", art_name );
        action.put( "data", data );

        LocalAgArch ag_arch = jason.infra.local.RunLocalMAS.getRunner().getAg( ag_name );
        VesnaAgent ag = ( VesnaAgent ) ag_arch.getTS().getAg();

        ag.perform( action.toString() ); 
        ag.addBel( parseLiteral( "grab(" + art_name + ")" ) );
    }

    @OPERATION
    public void release( String ag_region ) throws Exception {

        String ag_name = getCurrentOpAgentId().getAgentName();
        if ( ! owner.equals( ag_name ) ){
            log( "Agent " + ag_name + " was not grabbing the artifact" + art_name );
            failed( "Agent " + ag_name + " was not grabbing the artifact" + art_name );
        }

        owner = null;
        this.region = ag_region;
        log( ag_name + " releases " + art_name );

        JSONObject action = new JSONObject();
        action.put( "sender", ag_name );
        action.put( "receiver", "body" );
        action.put( "type", "interact" );
        JSONObject data = new JSONObject();
        data.put( "type", "release" );
        data.put( "art_name", art_name );
        action.put( "data", data );

        LocalAgArch ag_arch = jason.infra.local.RunLocalMAS.getRunner().getAg( ag_name );
        VesnaAgent ag = ( VesnaAgent ) ag_arch.getTS().getAg();

        ag.perform( action.toString() );
        ag.delBel( parseLiteral( "grab(" + art_name + ")" ) );
    }
    
}
