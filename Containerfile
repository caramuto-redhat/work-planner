FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (uses .containerignore)
COPY . .

# Accept build arguments for secrets
ARG JIRA_URL
ARG JIRA_API_TOKEN
ARG SLACK_XOXC_TOKEN
ARG SLACK_XOXD_TOKEN
ARG LOGS_CHANNEL_ID
ARG GEMINI_API_KEY

# Set environment variables from build arguments
ENV JIRA_URL=$JIRA_URL
ENV JIRA_API_TOKEN=$JIRA_API_TOKEN
ENV SLACK_XOXC_TOKEN=$SLACK_XOXC_TOKEN
ENV SLACK_XOXD_TOKEN=$SLACK_XOXD_TOKEN
ENV LOGS_CHANNEL_ID=$LOGS_CHANNEL_ID
ENV GEMINI_API_KEY=$GEMINI_API_KEY

# Entrypoint
CMD ["python", "server.py"] 