"""
Blog/CMS REST API — DevOps CBP
Resources: posts and comments, with full CRUD (GET, POST, PUT, PATCH, DELETE).
Database: PostgreSQL in Docker/Kubernetes, SQLite when run locally.
Monitoring: Prometheus metrics at /metrics. Logging: JSON lines to stdout.
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from prometheus_flask_exporter import PrometheusMetrics


# ---------- Logging (structured JSON so Loki/ELK/kubectl logs can parse it) ----------
class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        entry.update(getattr(record, "extra_fields", {}))
        return json.dumps(entry)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("blog")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False


# ---------- App + DB config ----------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///blog.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

metrics = PrometheusMetrics(app)
metrics.info("blog_app_info", "Blog CMS app info", version=os.getenv("APP_VERSION", "1.0.0"))
from prometheus_client import Counter  # noqa: E402

POSTS_CREATED = Counter("blog_posts_created", "Number of blog posts successfully created")


# ---------- Models ----------
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False, default="anonymous")
    published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    comments = db.relationship(
        "Comment", backref="post", cascade="all, delete-orphan", lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "published": self.published,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "comment_count": len(self.comments),
        }


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    author = db.Column(db.String(100), nullable=False, default="anonymous")
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "author": self.author,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


with app.app_context():
    db.create_all()


# ---------- Request logging ----------
@app.before_request
def start_timer():
    g.start = time.time()


@app.after_request
def log_request(response):
    if request.path != "/metrics":
        logger.info(
            "request",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round((time.time() - g.get("start", time.time())) * 1000, 2),
                }
            },
        )
    return response


def error(message, status):
    return jsonify({"error": message}), status


# ---------- Health ----------
@app.get("/")
def index():
    return jsonify({"app": "Blog CMS API", "version": os.getenv("APP_VERSION", "1.0.0"),
                    "endpoints": ["/api/posts", "/api/posts/<id>", "/api/posts/<id>/comments",
                                  "/api/comments/<id>", "/health", "/metrics"]})


@app.get("/health")
@metrics.do_not_track()
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ok", "database": "ok"})
    except Exception as exc:  # noqa: BLE001
        logger.error("health check failed", extra={"extra_fields": {"error": str(exc)}})
        return jsonify({"status": "error", "database": "down"}), 503


# ---------- Posts CRUD ----------
@app.get("/api/posts")
def list_posts():
    query = Post.query
    published = request.args.get("published")
    if published is not None:
        query = query.filter_by(published=published.lower() == "true")
    author = request.args.get("author")
    if author:
        query = query.filter_by(author=author)
    posts = query.order_by(Post.created_at.desc()).all()
    return jsonify([p.to_dict() for p in posts])


@app.get("/api/posts/<int:post_id>")
def get_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return error("Post not found", 404)
    return jsonify(post.to_dict())


@app.post("/api/posts")
def create_post():
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("content"):
        return error("'title' and 'content' are required", 400)
    post = Post(
        title=data["title"],
        content=data["content"],
        author=data.get("author", "anonymous"),
        published=bool(data.get("published", False)),
    )
    db.session.add(post)
    db.session.commit()
    POSTS_CREATED.inc()
    logger.info("post created", extra={"extra_fields": {"post_id": post.id}})
    return jsonify(post.to_dict()), 201


@app.put("/api/posts/<int:post_id>")
def replace_post(post_id):
    """PUT = full update: title and content are required."""
    post = db.session.get(Post, post_id)
    if not post:
        return error("Post not found", 404)
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("content"):
        return error("PUT requires 'title' and 'content'", 400)
    post.title = data["title"]
    post.content = data["content"]
    post.author = data.get("author", "anonymous")
    post.published = bool(data.get("published", False))
    db.session.commit()
    return jsonify(post.to_dict())


@app.patch("/api/posts/<int:post_id>")
def update_post(post_id):
    """PATCH = partial update: send only the fields you want to change."""
    post = db.session.get(Post, post_id)
    if not post:
        return error("Post not found", 404)
    data = request.get_json(silent=True) or {}
    allowed = {"title", "content", "author", "published"}
    if not allowed.intersection(data):
        return error(f"Send at least one of {sorted(allowed)}", 400)
    for field in allowed.intersection(data):
        setattr(post, field, bool(data[field]) if field == "published" else data[field])
    db.session.commit()
    return jsonify(post.to_dict())


@app.delete("/api/posts/<int:post_id>")
def delete_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return error("Post not found", 404)
    db.session.delete(post)
    db.session.commit()
    logger.info("post deleted", extra={"extra_fields": {"post_id": post_id}})
    return jsonify({"message": f"Post {post_id} deleted"})


# ---------- Comments CRUD ----------
@app.get("/api/posts/<int:post_id>/comments")
def list_comments(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return error("Post not found", 404)
    return jsonify([c.to_dict() for c in post.comments])


@app.post("/api/posts/<int:post_id>/comments")
def add_comment(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return error("Post not found", 404)
    data = request.get_json(silent=True) or {}
    if not data.get("body"):
        return error("'body' is required", 400)
    comment = Comment(post_id=post_id, body=data["body"], author=data.get("author", "anonymous"))
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201


@app.patch("/api/comments/<int:comment_id>")
def update_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return error("Comment not found", 404)
    data = request.get_json(silent=True) or {}
    if not data.get("body"):
        return error("'body' is required", 400)
    comment.body = data["body"]
    db.session.commit()
    return jsonify(comment.to_dict())


@app.delete("/api/comments/<int:comment_id>")
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return error("Comment not found", 404)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"message": f"Comment {comment_id} deleted"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
