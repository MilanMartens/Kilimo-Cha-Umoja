# docker build -t my-twilio-cli .
# docker run -p 5001:5001 -p 5002:5002 --env-file .env my-twilio-cli

# Start from Python
FROM python:3.12-slim

# Install Twilio CLI
RUN pip install twilio

# Set working directory
WORKDIR /app

# Copy your script
COPY ./WeatherAPI.py /app
COPY ./Message.py /app
COPY ./LocationAPI.py /app
COPY ./translator.py /app
COPY ./requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables (optional, can also pass at runtime)
ENV TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
ENV TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
ENV TWILIO_NUMBER =${TWILIO_NUMBER}
ENV TO_NUMBER =${to_number}
ENV TWILIO_API_KEY=${TWILIO_API_KEY}
ENV TWILIO_API_SECRET=${TWILIO_API_SECRET}

EXPOSE 5001
EXPOSE 5002

# Run your script
CMD ["python", "WeatherAPI.py", "--serve";"python","Message.py"]
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]