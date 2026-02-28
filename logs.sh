#!/bin/bash
# Quick log viewer for Slack connector

tail -f -n 50 /tmp/slack-connector.log /tmp/slack-connector-error.log
