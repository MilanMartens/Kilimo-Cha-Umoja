# Use the official MySQL image as base
FROM mysql:latest

# Environment variables from .env file
ENV MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
ENV MYSQL_DATABASE=${MYSQL_DATABASE}
ENV MYSQL_USER=${MYSQL_USER}
ENV MYSQL_PASSWORD=${MYSQL_PASSWORD}

# Copy init SQL scripts if needed (runs on first startup)
# COPY ./init.sql /docker-entrypoint-initdb.d/

# Expose MySQL port
EXPOSE 3306