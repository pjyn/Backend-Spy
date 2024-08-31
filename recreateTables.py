from app import app, db  # Import the Flask app and db instance

def recreate_tables():
    with app.app_context():  # Ensure you are within the application context
        # Drop all tables
        db.drop_all()
        print("Dropped all tables.")
        
        # Create all tables
        db.create_all()
        print("Created all tables.")

if __name__ == "__main__":
    recreate_tables()
