# Use Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy all files from the current directory to the container
COPY . .

# Command to run the Python script
CMD ["python", "main.py"]
