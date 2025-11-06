#!/usr/bin/env bash
set -e

echo "Adding Helm repositories..."
helm repo add altinity https://helm.altinity.com
# Add more repos here as needed
# helm repo add bitnami https://charts.bitnami.com/bitnami

echo "Updating Helm repositories..."
helm repo update

echo "Helm repositories configured successfully"
