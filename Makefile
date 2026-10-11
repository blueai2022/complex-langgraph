# Local development targets for the chat-quote LangGraph agent.

VENV := .venv

.PHONY: install test graph clean

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"

test:
	$(VENV)/bin/python -m pytest

graph:
	 $(VENV)/bin/python -m chat_quote_agent.main_graph

clean:
	rm -rf .pytest_cache src/*.egg-info
