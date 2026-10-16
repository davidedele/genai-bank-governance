# Builds the public demo on Hugging Face Spaces straight from the GitHub repository.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    GOVERNANCE_DEMO=1 \
    PORT=7860 \
    GOVERNANCE_DB_PATH=/tmp/register.sqlite
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
ADD https://github.com/davidedele/genai-bank-governance/archive/refs/heads/main.tar.gz /tmp/source.tar.gz
RUN tar -xzf /tmp/source.tar.gz --strip-components=1 \
    && rm /tmp/source.tar.gz \
    && pip install --no-cache-dir -r requirements.txt \
    && chown -R user:user /home/user/app
USER user
EXPOSE 7860
CMD ["python", "app.py"]
