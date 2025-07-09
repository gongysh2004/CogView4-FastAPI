# Environment Configuration

This project uses a centralized configuration system to manage API URLs across different environments.

## How it Works

The `config.js` file automatically detects the current environment based on the hostname and sets the appropriate API URL.

## Environment Detection

| Environment | Hostnames | API URL |
|------------|-----------|---------|
| **Production** | `your-production-domain.com`, `picmind.app` | `https://api.your-production-domain.com` |
| **Staging** | `staging.your-domain.com`, `dev.picmind.app` | `https://api-staging.your-domain.com` |
| **Development** | `localhost`, `127.0.0.1` | `http://localhost:8000` |
| **Local Network** | `192.168.*` | `http://192.168.95.192:8000` |

## Configuration File Structure

```javascript
// config.js
window.AppConfig = {
    environment: 'local',           // Current detected environment
    apiUrl: 'http://192.168.95.192:8000',  // API base URL
    isProduction: false,            // Boolean flag for production
    isDevelopment: false,           // Boolean flag for development
    debug: { ... }                  // Debug information
}
```

## Usage in JavaScript

```javascript
// Access the API URL
const API_BASE_URL = window.AppConfig.apiUrl;

// Check environment
if (window.AppConfig.isProduction) {
    // Production-specific code
}

// Debug information (only shown in non-production)
console.log('Current environment:', window.AppConfig.environment);
```

## Customizing Environments

To add or modify environments, edit the `environments` object in `config.js`:

```javascript
const environments = {
    yourNewEnv: {
        domains: ['your-new-domain.com'],
        apiUrl: 'https://api.your-new-domain.com'
    }
};
```

## Debugging

In non-production environments, the configuration will be logged to the browser console:

```
App Configuration: {
    environment: "local",
    apiUrl: "http://192.168.95.192:8000",
    isProduction: false,
    isDevelopment: false,
    debug: {
        hostname: "192.168.95.192",
        protocol: "http:",
        detectedEnv: "local",
        availableEnvs: ["production", "staging", "development", "local"]
    }
}
```

## File Structure

```
static/
├── config.js          # Environment configuration
├── index.html         # Main page (includes config.js)
├── gallery.html       # Gallery page (includes config.js)
└── ...
```

## Benefits

✅ **Automatic Detection**: No manual configuration needed  
✅ **Centralized**: One file manages all environments  
✅ **Debug-Friendly**: Logs configuration in development  
✅ **Flexible**: Easy to add new environments  
✅ **No Build Step**: Works without compilation  

## Production Deployment

1. Update the production domains in `config.js`
2. Ensure your production domain is listed in the `production.domains` array
3. Deploy the files - the configuration will automatically detect production

That's it! The system will automatically use the correct API URL based on where it's deployed. 