# general
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_path := $(subst Makefile,,$(mkfile_path))

# project
project_image_name := "clinic-chat"
project_container_name := "clinic-chat-container"
project_dir := "$(current_abs_path)"

.PHONY: build-only

build-only:
	docker build -t $(project_image_name) -f Dockerfile $(current_abs_path)

run-app: build-only
	docker run -it -v $(current_abs_path):/project -p 8501:8501 -t $(project_image_name) \
	streamlit run src/app.py

ingest: build-only
	docker run -it -v $(current_abs_path):/project -e REDIS_PASSWORD=$(REDIS_PASSWORD) -t $(project_image_name) \
	python src/ingest.py
