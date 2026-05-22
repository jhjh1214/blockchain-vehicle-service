from app import create_app
from db.models import db

app = create_app()

with app.app_context():
    db.drop_all()
    print("Dropped all tables")

    db.create_all()
    print("Created all tables")

    from sqlalchemy import inspect
    tables = inspect(db.engine).get_table_names()

    print("\nDatabase initialized successfully!")
    print("Tables created:")
    for table in tables:
        print(f"  - {table}")
