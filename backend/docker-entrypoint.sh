#!/bin/bash
set -e

echo "Starting Piper TTS API Docker container..."

# Create log directories
mkdir -p /app/logs
mkdir -p /var/log/nginx
mkdir -p /var/www/certbot
mkdir -p /var/log/supervisor

# Set permissions
chown -R www-data:www-data /var/log/nginx /app/logs /app/outputs
chmod -R 755 /app/logs /var/log/supervisor

# FIX: Add Piper to PATH
echo "Fixing Piper PATH..."
if [ -f "/usr/local/bin/piper/piper" ]; then
    # Create symlink to make piper accessible as just 'piper'
    ln -sf /usr/local/bin/piper/piper /usr/local/bin/piper-tts
    ln -sf /usr/local/bin/piper/piper /usr/bin/piper
    echo "Created symlinks for piper binary"
fi

# Export PATH to include piper location
export PATH="/usr/local/bin/piper:$PATH"

# Check for SSL certificates
SSL_CERT_PATH="/etc/letsencrypt/live/${DOMAIN:-localhost}"
SELF_SIGNED_CERT_PATH="/app/ssl"

if [ ! -d "$SSL_CERT_PATH" ] && [ ! -f "$SELF_SIGNED_CERT_PATH/server.crt" ]; then
    echo "No SSL certificates found. Creating self-signed certificates for development..."
    
    # Create SSL directory
    mkdir -p "$SELF_SIGNED_CERT_PATH"
    
    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SELF_SIGNED_CERT_PATH/server.key" \
        -out "$SELF_SIGNED_CERT_PATH/server.crt" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=${DOMAIN:-localhost}"
    
    echo "Self-signed certificates created at $SELF_SIGNED_CERT_PATH"
    
    # Update nginx configuration to use self-signed certificates
    sed -i "s|ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;|ssl_certificate $SELF_SIGNED_CERT_PATH/server.crt;|g" /etc/nginx/sites-available/default
    sed -i "s|ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;|ssl_certificate_key $SELF_SIGNED_CERT_PATH/server.key;|g" /etc/nginx/sites-available/default
fi

# Update nginx configuration with domain if provided
if [ ! -z "$DOMAIN" ]; then
    echo "Updating nginx configuration for domain: $DOMAIN"
    sed -i "s/server_name _;/server_name $DOMAIN;/g" /etc/nginx/sites-available/default
fi

# FIX: Enhanced CORS configuration in nginx
if [ ! -z "$FRONTEND_DOMAINS" ]; then
    echo "Frontend domains provided: $FRONTEND_DOMAINS"
    
    # Create a more comprehensive CORS configuration
    cat > /etc/nginx/conf.d/cors.conf << 'EOF'
# CORS configuration
map $http_origin $cors_origin_header {
    default "";
    "~^https://.*\.vercel\.app$" "$http_origin";
    "~^https://piperbox-.*\.vercel\.app$" "$http_origin";
    "http://localhost:3000" "$http_origin";
    "http://localhost:5173" "$http_origin";
    "https://localhost:3000" "$http_origin";
}

map $http_origin $cors_cred {
    default "";
    "~^https://.*\.vercel\.app$" "true";
    "~^https://piperbox-.*\.vercel\.app$" "true";
    "http://localhost:3000" "true";
    "http://localhost:5173" "true";
    "https://localhost:3000" "true";
}
EOF

    # Update the main nginx config to use CORS headers
    sed -i '/location \/ {/a \
        # CORS headers\
        add_header "Access-Control-Allow-Origin" $cors_origin_header always;\
        add_header "Access-Control-Allow-Methods" "GET, POST, OPTIONS" always;\
        add_header "Access-Control-Allow-Headers" "Accept,Authorization,Cache-Control,Content-Type,DNT,If-Modified-Since,Keep-Alive,Origin,User-Agent,X-Requested-With" always;\
        add_header "Access-Control-Allow-Credentials" $cors_cred always;\
        add_header "Access-Control-Max-Age" 1728000 always;\
        \
        # Handle preflight OPTIONS requests\
        if ($request_method = "OPTIONS") {\
            add_header "Access-Control-Allow-Origin" $cors_origin_header;\
            add_header "Access-Control-Allow-Methods" "GET, POST, OPTIONS";\
            add_header "Access-Control-Allow-Headers" "Accept,Authorization,Cache-Control,Content-Type,DNT,If-Modified-Since,Keep-Alive,Origin,User-Agent,X-Requested-With";\
            add_header "Access-Control-Allow-Credentials" $cors_cred;\
            add_header "Access-Control-Max-Age" 1728000;\
            add_header "Content-Type" "text/plain; charset=utf-8";\
            add_header "Content-Length" 0;\
            return 204;\
        }' /etc/nginx/sites-available/default
fi

# Test nginx configuration
echo "Testing nginx configuration..."
if ! nginx -t; then
    echo "ERROR: Nginx configuration test failed!"
    cat /etc/nginx/sites-available/default
    exit 1
fi

# Initialize Let's Encrypt if in production and domain is provided
if [ "$ENVIRONMENT" = "production" ] && [ ! -z "$DOMAIN" ] && [ ! -z "$EMAIL" ]; then
    echo "Setting up Let's Encrypt for domain: $DOMAIN"
    
    # Start nginx temporarily for certificate verification
    nginx &
    NGINX_PID=$!
    sleep 5
    
    # Get initial certificate
    if certbot certonly --webroot -w /var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN" \
        --non-interactive; then
        
        echo "Let's Encrypt certificate obtained successfully"
        
        # Update nginx to use Let's Encrypt certificates
        sed -i "s|ssl_certificate .*;|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|g" /etc/nginx/sites-available/default
        sed -i "s|ssl_certificate_key .*;|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|g" /etc/nginx/sites-available/default
        
        # Test configuration again
        nginx -t
        
        # Set up auto-renewal cron job
        echo "0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'nginx -s reload'" | crontab -
        
    else
        echo "Certificate generation failed, using self-signed certificates"
    fi
    
    # Stop temporary nginx
    kill $NGINX_PID 2>/dev/null || true
    wait $NGINX_PID 2>/dev/null || true
fi

# Verify piper installation
echo "Verifying piper installation..."
if command -v piper &> /dev/null; then
    echo "Piper TTS found: $(piper --help 2>&1 | head -n 1 || echo 'Piper available')"
else
    echo "WARNING: Piper TTS not found in PATH"
    echo "Checking if piper binary exists in expected locations..."
    find /usr -name "piper" -type f 2>/dev/null || echo "Piper binary not found"
    
    # Try to fix PATH issue
    if [ -f "/usr/local/bin/piper/piper" ]; then
        echo "Found piper at /usr/local/bin/piper/piper, adding to PATH"
        export PATH="/usr/local/bin/piper:$PATH"
    fi
fi

# Check voice models
echo "Checking voice models..."
VOICE_COUNT=$(find /app/piper_data -name "*.onnx" 2>/dev/null | wc -l)
echo "Found $VOICE_COUNT voice models"

if [ $VOICE_COUNT -eq 0 ]; then
    echo "WARNING: No voice models found. The API may not work properly."
    echo "Voice directories:"
    ls -la /app/piper_data/ 2>/dev/null || echo "piper_data directory not found"
fi

# Test Flask application
echo "Testing Flask application..."
cd /app
if python -c "import app; print('Flask app imports successfully')"; then
    echo "Flask application check passed"
else
    echo "ERROR: Flask application has import errors"
    exit 1
fi

# Environment-specific configurations
if [ "$ENVIRONMENT" = "development" ]; then
    echo "Running in development mode"
    export FLASK_ENV=development
    export FLASK_DEBUG=1
else
    echo "Running in production mode"
    export FLASK_ENV=production
    export FLASK_DEBUG=0
fi

# Create gunicorn PID directory
mkdir -p /app/logs
touch /app/logs/gunicorn.pid

# Set final permissions
chown -R www-data:www-data /app/logs /app/outputs
chmod 755 /app/logs /app/outputs

# FIX: Ensure PATH is available to gunicorn
echo "export PATH=\"/usr/local/bin/piper:\$PATH\"" >> /etc/environment

# Show final configuration summary
echo "=== Configuration Summary ==="
echo "Environment: ${ENVIRONMENT:-development}"
echo "Domain: ${DOMAIN:-localhost}"
echo "Email: ${EMAIL:-not-set}"
echo "Frontend Domains: ${FRONTEND_DOMAINS:-not-set}"
echo "SSL Cert Path: $(ls -la /etc/letsencrypt/live/ 2>/dev/null || echo 'Using self-signed')"
echo "Voice Models: $VOICE_COUNT found"
echo "PATH: $PATH"
echo "Piper Check: $(command -v piper && echo 'Found' || echo 'Not found')"
echo "Logs Directory: $(ls -la /app/logs/)"
echo "============================"

# Start supervisor (which manages gunicorn and nginx)
echo "Starting services with supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf