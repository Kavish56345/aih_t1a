# Use official Python image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code and folders
COPY . .

# Create output folder if it doesn't exist
RUN mkdir -p /app/output

# Run script
CMD ["python", "main.py"]
