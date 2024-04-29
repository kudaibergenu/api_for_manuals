#!/bin/bash

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
