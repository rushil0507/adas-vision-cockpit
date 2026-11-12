@echo off
title ADAS Public Tunnel for Netlify
echo =========================================================================
echo              CREATING SECURE PUBLIC TUNNEL FOR NETLIFY
echo =========================================================================
echo.
echo [*] Exposing your local ADAS backend (port 8000) to the public internet...
echo [*] This will generate a public HTTPS URL.
echo.
echo When prompted, open the URL and paste it into your Netlify dashboard!
echo Keep this window open while using your public Netlify dashboard.
echo =========================================================================
echo.

call npx localtunnel --port 8000
pause
