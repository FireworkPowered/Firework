#!/bin/bash

# 检查 src/firework/cli/config/__init__.py 是否被修改
if git diff --name-only --cached | grep -q 'src/firework/cli/config/__init__.py'; then
  # 如果文件改动了，运行 pdm run regenerate-cli-schema
  pdm run regenerate-cli-schema

  # 检查 src/firework/cli/config/schema.json 是否有改动
  if git diff --name-only --cached | grep -q 'src/firework/cli/config/schema.json'; then
    echo "Error: schema.json has been modified. Commit rejected."
    exit 1
  fi
fi

exit 0
