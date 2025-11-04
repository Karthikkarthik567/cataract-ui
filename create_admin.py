from app import app
from database import db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # (Optional) Reset DB completely
    db.drop_all()
    db.create_all()

    # Create new admin
    admin = User(
        username="Karthik33",
        email="hardikarthik33@gmail.com",
        password=generate_password_hash("Karthi@407"),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()

    print("✅ Fresh database created successfully!")
    print("👑 Admin created:", admin.email)
