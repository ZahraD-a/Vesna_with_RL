package vesna;

import cartago.Artifact;
import cartago.OPERATION;
import jason.infra.local.LocalAgArch;
import jason.infra.local.RunLocalMAS;
import jason.asSemantics.Agent;

import java.util.List;

import org.json.JSONObject;

import java.util.ArrayList;

public class SituatedArtifact extends Artifact{

    private String region;
    private String art_name;
    private int limit;
    private List<String> using;

    public String get_art_name() {
        return this.art_name;
    }

    public void init( String region, int limit ) {
        this.region = region;
        this.limit = limit;
        using = new ArrayList<String>();
        this.art_name = getId().getName();
        log( "Artifact name: " + art_name );
        log( "Init finished!" );
    }

    @OPERATION
    public void use( String ag_region ) {

        if ( ! ag_region.equals( this.region ) ) {
            failed( "You cannot use this artifact: it is in another region!" );
        }

        if ( using.size() >= limit )
            failed( "You cannot use " + art_name + " because it is already used by other agent(s)" );
        
        String ag_name = getCurrentOpAgentId().getAgentName();
        if ( using.contains( ag_name ) ) {
            log( "Agent " + ag_name + "is already using the artifact!" );
            return;
        }

        using.add( ag_name );
        log( ag_name + " can use " + this.art_name );

        JSONObject action = new JSONObject();
        action.put( "sender", ag_name );
        action.put( "receiver", "body" );
        action.put( "type", "interact" );
        JSONObject data = new JSONObject();
        data.put( "type", "use" );
        data.put( "art_name", art_name );
        action.put( "data", data );

        LocalAgArch ag_arch = jason.infra.local.RunLocalMAS.getRunner().getAg( ag_name );
        VesnaAgent ag = ( VesnaAgent ) ag_arch.getTS().getAg();

        ag.perform( action.toString() ); 
    }

    @OPERATION
    public void free( ) throws Exception {

        String ag_name = getCurrentOpAgentId().getAgentName();
        if ( ! using.contains( ag_name ) ) {
            log( "Agent " + ag_name + " was not using the artifact!" );
            return;
        }

        using.remove( ag_name );
        log( ag_name + " frees " + art_name );

        JSONObject action = new JSONObject();
        action.put( "sender", ag_name );
        action.put( "receiver", "body" );
        action.put( "type", "interact" );
        JSONObject data = new JSONObject();
        data.put( "type", "free" );
        data.put( "art_name", art_name );
        action.put( "data", data );

        LocalAgArch ag_arch = jason.infra.local.RunLocalMAS.getRunner().getAg( ag_name );
        VesnaAgent ag = ( VesnaAgent ) ag_arch.getTS().getAg();

        ag.perform( action.toString() ); 
    }

    public boolean is_using( String ag_name ) {
        return using.contains( ag_name );
    }
    
}
