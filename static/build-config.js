// This file can be replaced during build time
window.BuildConfig = {
    API_BASE_URL: '{{API_BASE_URL}}', // Will be replaced by build script
    ENVIRONMENT: '{{ENVIRONMENT}}',   // Will be replaced by build script
    VERSION: '{{VERSION}}'            // Will be replaced by build script
};

// Fallback if build variables are not replaced
if (window.BuildConfig.API_BASE_URL.includes('{{')) {
    window.BuildConfig.API_BASE_URL = 'http://192.168.95.192:8000';
    window.BuildConfig.ENVIRONMENT = 'development';
    window.BuildConfig.VERSION = 'dev';
} 