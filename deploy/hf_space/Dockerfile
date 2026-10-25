# NailIQ on a Hugging Face Docker Space: Flask API + the built web app on one port (7860), CPU only.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir torch==2.12.1 torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user . .
USER user

# NAILIQ_REQUIRE_CLIENT_ID: History only ever shows a browser its own scans. The database is temporary (resets when
# the Space restarts) and stores findings only - photos are analyzed in memory and never saved.
ENV NAILIQ_STATIC_DIR=/home/user/app/frontend/dist \
    NAILIQ_REQUIRE_CLIENT_ID=1 \
    NAILIQ_TRUST_PROXY=1 \
    NAILIQ_DATABASE_URI=sqlite:////tmp/nailiq.db \
    PYTHONUNBUFFERED=1

EXPOSE 7860
# fetch_models.py pulls the weights from the private model repo (see its docstring), then the server starts
CMD ["sh", "-c", "python fetch_models.py && exec gunicorn --chdir backend -b 0.0.0.0:7860 --workers 1 --threads 4 --timeout 180 app:app"]
