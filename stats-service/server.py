import stats_pb2, stats_pb2_grpc
from clickhouse_driver import Client

client = Client(
    host='clickhouse',
    user='admin',
    password='admin123',
    database='default'
)

class StatsService(stats_pb2_grpc.StatsServiceServicer):
    def GetPostStats(self, request, context):
        post_id = request.post_id
        views = client.execute(
            "SELECT count() FROM post_views WHERE post_id = %(post_id)s",
            {'post_id': post_id}
        )[0][0]

        likes = client.execute(
            "SELECT count() FROM post_likes WHERE post_id = %(post_id)s",
            {'post_id': post_id}
        )[0][0]

        comments = client.execute(
            "SELECT count() FROM post_comments WHERE post_id = %(post_id)s",
            {'post_id': post_id}
        )[0][0]

        return stats_pb2.PostStatsResponse(views=views, likes=likes, comments=comments)

    def GetPostViewsOverTime(self, request, context):
        rows = client.execute("""
            SELECT toDate(viewed_at) as day, count()
            FROM post_views
            WHERE post_id = %(post_id)s
            GROUP BY day ORDER BY day
        """, {'post_id': request.post_id})

        return stats_pb2.TimeSeriesResponse(
            entries=[stats_pb2.TimeSeriesEntry(date=row[0].isoformat(), count=row[1]) for row in rows]
        )

    def GetPostLikesOverTime(self, request, context):
        rows = client.execute("""
            SELECT toDate(liked_at) as day, count()
            FROM post_likes
            WHERE post_id = %(post_id)s
            GROUP BY day ORDER BY day
        """, {'post_id': request.post_id})

        return stats_pb2.TimeSeriesResponse(
            entries=[stats_pb2.TimeSeriesEntry(date=row[0].isoformat(), count=row[1]) for row in rows]
        )

    def GetPostCommentsOverTime(self, request, context):
        rows = client.execute("""
            SELECT toDate(commented_at) as day, count()
            FROM post_comments
            WHERE post_id = %(post_id)s
            GROUP BY day ORDER BY day
        """, {'post_id': request.post_id})

        return stats_pb2.TimeSeriesResponse(
            entries=[stats_pb2.TimeSeriesEntry(date=row[0].isoformat(), count=row[1]) for row in rows]
        )

    def GetTopPosts(self, request, context):
        table = f"post_{request.metric}"
        rows = client.execute(f"""
            SELECT post_id, count() AS cnt
            FROM {table}
            GROUP BY post_id
            ORDER BY cnt DESC
            LIMIT 10
        """)
        return stats_pb2.TopPostsResponse(
            posts=[stats_pb2.PostEntry(post_id=row[0], count=row[1]) for row in rows]
        )

    def GetTopUsers(self, request, context):
        table = f"post_{request.metric}"
        rows = client.execute(f"""
            SELECT user_id, count() AS cnt
            FROM {table}
            GROUP BY user_id
            ORDER BY cnt DESC
            LIMIT 10
        """)
        return stats_pb2.TopUsersResponse(
            users=[stats_pb2.UserEntry(user_id=row[0], count=row[1]) for row in rows]
        )
