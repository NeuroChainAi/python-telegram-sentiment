# Base image with Python 3.10
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy the current directory content to the container
COPY . /app

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot script
CMD ["python", "bot.py"]
