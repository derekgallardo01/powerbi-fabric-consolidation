# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir --quiet pytest

# Default command runs the campgrounds dashboard build. Override:
#   docker run --rm -v $(pwd)/out:/app/out <image>                             # bind out/ to host
#   docker run --rm <image> python cli.py --variance-threshold 2.0
#   docker run --rm <image> python cli.py --data data-hospitality
#   docker run --rm <image> python evals/run.py
#   docker run --rm <image> python -m pytest -q
CMD ["python", "run.py"]
