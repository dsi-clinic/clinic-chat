# general
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_path := $(subst Makefile,,$(mkfile_path))

# project
app_image_name := "clinic-chat-app"
backend_image_name := "clinic-chat-backend"

.PHONY: build-app build-backend

build-app:
	docker build -t $(app_image_name) -f docker/Dockerfile.client $(current_abs_path)

build-backend:
	docker build -t $(backend_image_name) -f docker/Dockerfile.backend $(current_abs_path)

run-app: build-app
	docker run -it -v $(current_abs_path):/app -p 8501:8501 -t $(app_image_name) \
	streamlit run src/app.py

run-ingest: build-backend
	docker run -v $(current_abs_path):/project \
		-e REDIS_PASSWORD=$(REDIS_PASSWORD) \
		-e REDIS_HOST=$(REDIS_HOST) \
		-e REDIS_PORT=$(REDIS_PORT) \
		-e OPENAI_API_KEY=$(OPENAI_API_KEY) \
		$(backend_image_name) \
		uv run python src/ingest.py