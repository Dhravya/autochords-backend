# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables to make Python non-buffered and without .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /usr/src/app

# Install FFmpeg
RUN apt-get install -y ffmpeg \
    && apt-get install -y libsndfile-dev \
    && pip install audioread \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at the working directory
COPY . .

# If you have a requirements.txt file, copy it into the container and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Run main.py when the container launches
CMD ["python", "./main.py"]
