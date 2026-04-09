FROM python:3.11-slim

WORKDIR /app

# Copy package files
COPY pyproject.toml ./
COPY razorpay_docs_mcp/ ./razorpay_docs_mcp/

# Install the package and its dependencies
RUN pip install --no-cache-dir -e .

# The DuckDB database lives in /app/data at runtime.
# Before starting the server for the first time, build the database with:
#   docker compose run --rm mcp python -m razorpay_docs_mcp.refresh
VOLUME ["/app/data"]

EXPOSE 8000

CMD ["python", "-m", "razorpay_docs_mcp.server", "--transport", "http", "--port", "8000"]
