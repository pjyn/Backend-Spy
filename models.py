from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(36), nullable=False, unique=True)
    product_name = db.Column(db.String(100), nullable=False)  # Update here
    input_image_urls = db.Column(db.Text, nullable=False)
    output_image_urls = db.Column(db.Text)  # Column for output URLs
    status = db.Column(db.String(20), nullable=False)
