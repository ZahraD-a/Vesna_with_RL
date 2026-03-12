package rl;

import jason.asSemantics.*;
import jason.asSyntax.*;

import java.util.concurrent.TimeUnit;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;

import rl_service.RLServiceGrpc;
import rl_service.RlService.*;

/**
 * Internal action to save the current model checkpoint via gRPC.
 * Calls SaveModel on the Python gRPC RL service.
 *
 * Usage in ASL:
 *   rl.save_model
 *
 * Saves to: checkpoints/shared_agent.pt (or specified path)
 */
public class save_model extends DefaultInternalAction {

    private static final String GRPC_HOST = "localhost";
    private static final int GRPC_PORT = 50051;
    private static ManagedChannel grpcChannel;
    private static RLServiceGrpc.RLServiceBlockingStub grpcStub;

    static {
        initGrpc();
    }

    private static synchronized void initGrpc() {
        if (grpcChannel == null || grpcChannel.isShutdown()) {
            grpcChannel = ManagedChannelBuilder
                    .forAddress(GRPC_HOST, GRPC_PORT)
                    .usePlaintext()
                    .enableRetry()
                    .maxRetryAttempts(3)
                    .build();
            grpcStub = RLServiceGrpc.newBlockingStub(grpcChannel);
        }
    }

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        String agentName = ts.getAgArch().getAgName();

        try {
            // Ensure channel is ready
            if (grpcChannel == null || grpcChannel.isShutdown()) {
                initGrpc();
            }

            SaveRequest request = SaveRequest.newBuilder()
                    .setCheckpointPath("")  // Use default path
                    .build();

            SaveResponse response = grpcStub.withDeadlineAfter(30, TimeUnit.SECONDS)
                    .saveModel(request);

            if (response.getSuccess()) {
                String path = response.getSavedPath();
                System.out.println("[" + agentName + "] Model saved to: " + path);
                return true;
            } else {
                System.err.println("[" + agentName + "] Failed to save model: " + response.getMessage());
                return false;
            }
        } catch (Exception e) {
            System.err.println("[" + agentName + "] gRPC save failed: " + e.getMessage());
            return false;
        }
    }
}
