from celery import Celery
from PIL import Image
import requests
from io import BytesIO
from config import Config
from models import db, Product
import logging

celery = Celery(__name__, broker=Config.CELERY_BROKER_URL, backend=Config.CELERY_RESULT_BACKEND)

@celery.task
def process_images(request_id):
    from app import app

    with app.app_context():
        logging.info(f"Started processing images for request_id: {request_id}")
        products = Product.query.filter_by(request_id=request_id).all()
        if not products:
            logging.error(f"No products found for request_id: {request_id}")
            return

        for product in products:
            input_urls = product.input_image_urls.split(',')
            output_urls = []

            for url in input_urls:
                try:
                    logging.info(f"Processing image from URL: {url}")
                    response = requests.get(url)
                    response.raise_for_status()  # Ensure we get a successful response

                    img = Image.open(BytesIO(response.content))
                    img = img.resize((img.width // 2, img.height // 2))  # Resize to 50%
                    output_url = f"processed_{url.split('/')[-1]}"

                    # Check the output path
                    logging.info(f"Saving processed image to: {output_url}")
                    img.save(output_url)

                    output_urls.append(output_url)
                    logging.info(f"Processed image from URL: {url} and saved to {output_url}")
                except Exception as e:
                    logging.error(f"Failed to process image from URL: {url} with error: {e}")
                    continue  # Skip this URL and move to the next one

            # Log the final output URLs before committing to the database
            logging.info(f"Output URLs for product {product.product_name}: {output_urls}")

            if output_urls:
                product.output_image_urls = ','.join(output_urls)
                product.status = 'Completed'
            else:
                product.status = 'Failed'  # Mark as failed if no output URLs were generated

            logging.info(f"Processed product {product.product_name} with status {product.status} and output URLs: {product.output_image_urls}")

        try:
            db.session.commit()
            logging.info(f"Completed processing for request_id: {request_id}")
        except Exception as e:
            logging.error(f"Failed to commit changes to the database for request_id: {request_id} with error: {e}")


