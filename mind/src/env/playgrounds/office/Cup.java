package vesna.playgrounds.office;

import cartago.INTERNAL_OPERATION;
import vesna.GrabbableArtifact;

public class Cup extends GrabbableArtifact {
    
    String content = null;

    @INTERNAL_OPERATION
    public void set_content( String content ) {
        this.content = content;
        log( "New content is " + content );
    }

}
