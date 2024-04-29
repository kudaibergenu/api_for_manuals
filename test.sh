#!/bin/bash

# Build the Docker image
docker build -t myflaskapp .

# Run the Docker container
docker run -d --name myflaskcontainer -p 5000:5000 myflaskapp

# Wait for the container to fully start and the Flask app to be ready
echo "Waiting for the Flask app to start..."
sleep 10

# Endpoint of the Flask API
API_ENDPOINT="http://127.0.0.1:5000/process-pdf"

# Location of the Fan Manual PDF on your local system
PDF_FILE_PATH="files/Fan Manual.pdf"

# Pages to process
PAGES="9"

# Make the API call with the PDF file and the pages
curl -X POST "$API_ENDPOINT" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@\"$PDF_FILE_PATH\";type=application/pdf" \
     -F "pages=$PAGES"

# Optionally, you could add a command to stop and remove the container after the API call
docker stop myflaskcontainer
docker rm myflaskcontainer
