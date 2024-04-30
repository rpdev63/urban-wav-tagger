FROM python:3.10-slim

# Set a directory for the app
WORKDIR /usr/src/flask_app

# Copy all the files to the container
COPY . .

# Install dependencies
RUN apt-get update
RUN apt-get install -y libsndfile1 ffmpeg
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Arguments that can be passed at build time
ARG API_ENDPOINT
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY

# Environment variables
ENV API_ENDPOINT=${API_ENDPOINT}
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

# Tell the port number the container should expose
EXPOSE 5000
# Generate a session key and run the application
CMD FLASK_SESSION_KEY=$(openssl rand -base64 32) && \
    export FLASK_SESSION_KEY && \
    echo "FLASK_SESSION_KEY set to $FLASK_SESSION_KEY" && \
    python ./app.py
