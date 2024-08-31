from flask import Flask, request, jsonify, Response
from models import db, Product
from config import Config, make_celery
import uuid
import io
import csv
import pandas as pd
import logging
from sqlalchemy.exc import IntegrityError
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config.from_object(Config)

# Initialize Database and Celery
db.init_app(app)
celery = make_celery(app)

# Import here to avoid circular import issues
from tasks import process_images

@app.before_first_request
def create_tables():
    db.create_all()

## CSV Handling
@app.route('/upload', methods=['POST'])
def upload_csv():
    logging.info("Received upload request")
    file = request.files.get('file')
    if not file:
        logging.error("No file uploaded")
        return jsonify({"error": "No file uploaded"}), 400

    try:
        # Read CSV into DataFrame
        df = pd.read_csv(file)
        logging.info(f"CSV parsed successfully: {df.shape[0]} rows found")

        # Track inserted product names to avoid conflicts
        request_ids = []

        for index, row in df.iterrows():
            request_id = str(uuid.uuid4())  # Generate a new request_id for each product
            product = Product(
                request_id=request_id,
                product_name=row['Product Name'],
                input_image_urls=row['Input Image Urls'],
                status='Pending'
            )
            db.session.add(product)
            logging.info(f"Added product: {row['Product Name']} with request_id: {request_id}")
            request_ids.append(request_id)

        db.session.commit()
        logging.info("Database commit successful")

        # Start async image processing task for each request_id
        for request_id in request_ids:
            process_images.delay(request_id)
            logging.info(f"Started async image processing task for request_id: {request_id}")
        
        return jsonify({"message": "Upload successful", "request_ids": request_ids}), 202

    except pd.errors.EmptyDataError:
        logging.error("The uploaded CSV file is empty")
        return jsonify({"error": "Empty CSV file"}), 400

    except IntegrityError as e:
        logging.error(f"IntegrityError: {str(e)} - Likely due to duplicate request_id")
        db.session.rollback()
        return jsonify({"error": "Duplicate request ID encountered"}), 400

    except Exception as e:
        logging.error(f"Error processing upload: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to process CSV"}), 500



@app.route('/status/<file_request_id>', methods=['GET'])
def check_status(file_request_id):
    logging.info(f"Checking status for request ID: {file_request_id}")

    # Query for products associated with the file_request_id
    products = Product.query.filter_by(request_id=file_request_id).all()

    if not products:
        logging.error("Request ID not found")
        return jsonify({"error": "Request ID not found"}), 404

    # Prepare a response with product details
    product_list = []
    for product in products:
        product_list.append({
            "product_name": product.product_name,
            "input_image_urls": product.input_image_urls,
            "output_image_urls": product.output_image_urls,
            "status": product.status
        })

    return jsonify({"products": product_list}), 200


##  Create an Endpoint to Generate the Output CSV
@app.route('/export/<request_id>', methods=['GET'])
def export_csv(request_id):
    product = Product.query.filter_by(request_id=request_id).first()
    if not product:
        return jsonify({"error": "Request ID not found"}), 404

    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV headers
    writer.writerow(['Serial Number', 'Product Name', 'Input Image Urls', 'Output Image Urls'])

    # Write CSV data
    writer.writerow([
        product.id,
        product.product_name,
        product.input_image_urls,
        product.output_image_urls
    ])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=output_{request_id}.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)
