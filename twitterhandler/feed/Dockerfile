# Use an official Python runtime as a parent image
FROM python:3.5.6-alpine3.8

# Set the working directory to /app
WORKDIR /usr/src/app

# Copy requirements.txt
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Run twitter-user-profile3.py when the container lunches
CMD ["python", "./twitter-account-tweets.py"]

