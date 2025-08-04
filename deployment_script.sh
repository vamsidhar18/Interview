#!/bin/bash

# Amazon SDE II Interview Prep Tool - Deployment Script
# This script helps you deploy to Streamlit Cloud

echo "🚀 Amazon SDE II Interview Prep Tool - Deployment Guide"
echo "======================================================="

echo ""
echo "📋 Pre-deployment Checklist:"
echo "1. ✅ Create a GitHub repository"
echo "2. ✅ Push all files to the repository"
echo "3. ✅ Get Claude API key from https://console.anthropic.com/"
echo "4. ✅ Sign up for Streamlit Cloud at https://share.streamlit.io/"

echo ""
echo "📁 Required Files Structure:"
echo "your-repo/"
echo "├── main_app.py"
echo "├── requirements.txt"
echo "├── README.md"
echo "└── .streamlit/"
echo "    └── config.toml"

echo ""
echo "🔧 Steps to Deploy:"
echo "1. Go to https://share.streamlit.io/"
echo "2. Connect your GitHub account"
echo "3. Select your repository"
echo "4. Set main file path: main_app.py"
echo "5. Deploy!"

echo ""
echo "🌐 Your app will be available at:"
echo "https://[your-username]-[your-repo-name]-[branch]-[random-hash].streamlit.app/"

echo ""
echo "⚡ For local testing:"
echo "pip install -r requirements.txt"
echo "streamlit run main_app.py"

echo ""
echo "🔑 Don't forget to enter your Claude API key in the sidebar after deployment!"
