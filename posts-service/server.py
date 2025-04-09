import grpc
from concurrent import futures
import time
import uuid
import datetime

import post_pb2
import post_pb2_grpc

from google.protobuf.timestamp_pb2 import Timestamp

posts_db = {}

class PostService(post_pb2_grpc.PostServiceServicer):
    def CreatePost(self, request, context):
        post_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        post = post_pb2.Post(
            id=post_id,
            title=request.title,
            description=request.description,
            creator_id=request.creator_id,
            created_at=now,
            updated_at=now,
            is_private=request.is_private,
            tags=request.tags
        )
        posts_db[post_id] = post
        return post_pb2.PostResponse(post=post)

    def GetPost(self, request, context):
        post = posts_db.get(request.id)
        if not post:
            context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
        if post.is_private and post.creator_id != request.requester_id:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Access denied")
        return post_pb2.PostResponse(post=post)

    def UpdatePost(self, request, context):
        post = posts_db.get(request.id)
        if not post:
            context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
        if post.creator_id != request.requester_id:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Access denied")
        updated_post = post_pb2.Post(
            id=post.id,
            title=request.title or post.title,
            description=request.description or post.description,
            creator_id=post.creator_id,
            created_at=post.created_at,
            updated_at=datetime.datetime.utcnow().isoformat(),
            is_private=request.is_private,
            tags=request.tags
        )
        posts_db[post.id] = updated_post
        return post_pb2.PostResponse(post=updated_post)

    def DeletePost(self, request, context):
        post = posts_db.get(request.id)
        if not post:
            context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
        if post.creator_id != request.requester_id:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Access denied")
        del posts_db[request.id]
        return post_pb2.Empty()

    def ListPosts(self, request, context):
        filtered_posts = [p for p in posts_db.values() if not p.is_private or p.creator_id == request.requester_id]
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        return post_pb2.ListPostsResponse(posts=filtered_posts[start:end])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    post_pb2_grpc.add_PostServiceServicer_to_server(PostService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("PostService gRPC server running on port 50051")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()

