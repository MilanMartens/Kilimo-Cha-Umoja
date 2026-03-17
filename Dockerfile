# Use the official Twilio CLI image as base
FROM twilio/twilio-cli:latest

# Set environment variables for Twilio credentials
# These should be passed at runtime via --env or docker-compose
ENV TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
ENV TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
ENV TWILIO_API_KEY=${TWILIO_API_KEY}
ENV TWILIO_API_SECRET=${TWILIO_API_SECRET}

# Set working directory
WORKDIR /app

# Copy any local scripts or config files if needed
# COPY ./scripts /app/scripts

# Optional: pre-install Twilio CLI plugins
# RUN twilio plugins:install @twilio-labs/plugin-serverless
# RUN twilio plugins:install @twilio-labs/plugin-flex

# Default command to verify the Twilio CLI installation
CMD ["twilio", "--version"]
