import threading
from concurrent import futures
import grpc
import stats_pb2_grpc
from server import StatsService
from consumer import create_tables, run_kafka_consumer

def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    stats_pb2_grpc.add_StatsServiceServicer_to_server(StatsService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("✅ gRPC server started on port 50052")
    server.wait_for_termination()

if __name__ == "__main__":
    print("📦 Creating tables...")
    create_tables()

    print("🚀 Starting Kafka consumer...")
    consumer_thread = threading.Thread(target=run_kafka_consumer, daemon=True)
    consumer_thread.start()

    print("🚀 Starting gRPC server...")
    serve_grpc()
