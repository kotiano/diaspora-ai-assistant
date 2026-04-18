import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

from config import get_config

load_dotenv()

db      = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)

    cfg = config_class or get_config()
    app.config.from_object(cfg)


    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")

    if not db_uri:
        instance_path = os.path.join(app.root_path, '..', 'instance')
        instance_path = os.path.abspath(instance_path)
        os.makedirs(instance_path, exist_ok=True)
        db_uri = f"sqlite:///{os.path.join(instance_path, 'diaspora.db')}"
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        print(f"[INFO] DB URI was empty — using fallback: {db_uri}")

    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "", 1)
        db_dir  = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    print(f"[INFO] Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.home  import main_bp
    from app.routes.tasks import tasks_bp
    from app.routes.api   import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(tasks_bp, url_prefix="/tasks")
    app.register_blueprint(api_bp,   url_prefix="/api")

    with app.app_context():
        db.create_all()

    return app