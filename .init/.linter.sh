#!/bin/bash
cd /home/kavia/workspace/code-generation/ai-copilot-chat-application-4349/ai_copilot_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

