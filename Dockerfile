# Use Python 3.9 image (Stable for geospatial libs)
FROM python:3.9

# Set the working directory to /code
WORKDIR /code

# Copy the requirements file
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
# We add --no-cache-dir to keep the image small
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the application code
COPY . /code

# Create a writable directory for cache/temp files (Important for OSMnx on HF)
RUN mkdir -p /code/cache && chmod 777 /code/cache

# Set environment variables for OSMnx to use the writable cache
ENV OSMNX_CACHE_FOLDER=/code/cache

# Expose port 7860 (Hugging Face specific port)
EXPOSE 7860

# Command to run the application using Gunicorn
# "app:app" means file named app.py, variable named app
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]