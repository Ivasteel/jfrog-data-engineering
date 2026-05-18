FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir pytest

CMD ["sh", "-c", \
    "python3 task2_ai_assisted_pipeline/scripts/run_pipeline.py && \
     python3 -m pytest task2_ai_assisted_pipeline/tests/test_review_agent.py -v"]
