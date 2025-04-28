import grpc
from concurrent import futures
import uuid
import datetime

from sqlalchemy import create_engine, Column, String, Boolean, Text, ARRAY, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import post_pb2
import post_pb2_grpc

DATABASE_URL = "postgresql://user_admin:password@postgres-db-posts:5432/posts_db"

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class Post(Base):
    __tablename__ = 'posts'

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    creator_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_private = Column(Boolean, default=False)  # Simple boolean column
    tags = Column(ARRAY(String), default=[])

class PostView(Base):
    __tablename__ = 'post_views'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String, nullable=False)
    viewer_id = Column(String, nullable=False)
    viewed_at = Column(DateTime, default=datetime.datetime.utcnow)

class PostLike(Base):
    __tablename__ = 'post_likes'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String, nullable=False)
    liker_id = Column(String, nullable=False)
    liked_at = Column(DateTime, default=datetime.datetime.utcnow)

class PostComment(Base):
    __tablename__ = 'post_comments'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String, nullable=False)
    commenter_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    commented_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(engine)

class PostService(post_pb2_grpc.PostServiceServicer):
    def CreatePost(self, request, context):
        session = Session()
        try:
            post_id = str(uuid.uuid4())
            now = datetime.datetime.utcnow()

            post = Post(
                id=post_id,
                title=request.title,
                description=request.description,
                creator_id=request.creator_id,
                created_at=now,
                updated_at=now,
                is_private=request.is_private,
                tags=list(request.tags)
            )

            session.add(post)
            session.commit()
            session.refresh(post)

            return post_pb2.PostResponse(post=self.to_proto(post))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error creating post: {str(e)}")
        finally:
            session.close()

    def GetPost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter_by(id=request.id).first()
            if not post:
                context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
            
            # Check if post is private and if requester is not the creator
            if post.is_private and request.requester_id != post.creator_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Access denied to private post")
                
            return post_pb2.PostResponse(post=self.to_proto(post))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error retrieving post: {str(e)}")
        finally:
            session.close()

    def UpdatePost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter_by(id=request.id).first()
            if not post:
                context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
            if post.creator_id != request.requester_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Access denied: not the creator")

            post.title = request.title or post.title
            post.description = request.description or post.description
            post.is_private = request.is_private
            post.tags = list(request.tags)
            post.updated_at = datetime.datetime.utcnow()

            session.commit()
            return post_pb2.PostResponse(post=self.to_proto(post))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error updating post: {str(e)}")
        finally:
            session.close()

    def DeletePost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter_by(id=request.id).first()
            if not post:
                context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
            if post.creator_id != request.requester_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Access denied: not the creator")

            session.delete(post)
            session.commit()
            return post_pb2.Empty()
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error deleting post: {str(e)}")
        finally:
            session.close()

    def ListPosts(self, request, context):
        session = Session()
        try:
            posts_query = session.query(Post).filter(
                (Post.is_private == False) | (Post.creator_id == request.requester_id)
            ).order_by(Post.created_at.desc())

            start = (request.page - 1) * request.page_size
            end = start + request.page_size

            posts = posts_query.slice(start, end).all()
            return post_pb2.ListPostsResponse(posts=[self.to_proto(p) for p in posts])
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error listing posts: {str(e)}")
        finally:
            session.close()

    def ViewPost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter_by(id=request.post_id).first()
            if not post:
                context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
            
            view = PostView(
                post_id=request.post_id,
                viewer_id=request.viewer_id,
                viewed_at=datetime.datetime.fromisoformat(request.viewed_at)
            )
            session.add(view)
            session.commit()
            return post_pb2.Empty()
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error viewing post: {str(e)}")
        finally:
            session.close()

    def LikePost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter_by(id=request.post_id).first()
            if not post:
                context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
            
            like = PostLike(
                post_id=request.post_id,
                liker_id=request.liker_id,
                liked_at=datetime.datetime.fromisoformat(request.liked_at)
            )
            session.add(like)
            session.commit()
            return post_pb2.Empty()
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error liking post: {str(e)}")
        finally:
            session.close()

    def CommentPost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter_by(id=request.post_id).first()
            if not post:
                context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
            
            comment = PostComment(
                post_id=request.post_id,
                commenter_id=request.commenter_id,
                content=request.content,
                commented_at=datetime.datetime.fromisoformat(request.commented_at)
            )
            session.add(comment)
            session.commit()
            return post_pb2.Empty()
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error commenting on post: {str(e)}")
        finally:
            session.close()

    def ListPostComments(self, request, context):
        session = Session()
        try:
            comments_query = session.query(PostComment).filter_by(post_id=request.post_id).order_by(PostComment.commented_at.desc())

            start = (request.page - 1) * request.page_size
            end = start + request.page_size
            comments = comments_query.slice(start, end).all()

            return post_pb2.ListPostCommentsResponse(comments=[
                post_pb2.Comment(
                    id=c.id,
                    post_id=c.post_id,
                    commenter_id=c.commenter_id,
                    content=c.content,
                    commented_at=c.commented_at.isoformat()
                ) for c in comments
            ])
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error listing comments: {str(e)}")
        finally:
            session.close()


    def to_proto(self, post):
        return post_pb2.Post(
            id=post.id,
            title=post.title,
            description=post.description,
            creator_id=post.creator_id,
            created_at=post.created_at.isoformat(),
            updated_at=post.updated_at.isoformat(),
            is_private=post.is_private,
            tags=post.tags
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    post_pb2_grpc.add_PostServiceServicer_to_server(PostService(), server)
    server.add_insecure_port('[::]:50051')
    print("PostService gRPC server running on port 50051")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
