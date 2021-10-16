FROM python:3.9

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
		jq \
	&& rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 fastapi \
  && useradd --uid 1000 --gid fastapi --shell /bin/bash --create-home fastapi \
  && chown fastapi:fastapi /code

COPY ./app/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY --chown=fastapi:fastapi ./compose/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
COPY ./app /code/app

USER fastapi

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]