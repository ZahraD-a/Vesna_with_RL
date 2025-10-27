package vesna;

public interface WsClientMsgHandler {
    
    public void handleMsg( String msg );
    public void handleError( Exception ex );
}
