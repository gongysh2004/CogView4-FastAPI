// Environment Configuration
window.AppConfig = (function() {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    // Environment detection
    const environments = {
        production: {
            domains: ['picmind.dev.ai-links.com'],
            apiUrl: 'https://picmind.dev.ai-links.com'
        },
        staging: {
            domains: ['staging.your-domain.com', 'dev.picmind.app', 'test.picmind.app'],
            apiUrl: 'https://api-staging.your-domain.com'
        },
        local: {
            domains: ['localhost', '127.0.0.1', '0.0.0.0'],
            apiUrl: 'http://localhost:8000'
        },
        development: {
            domains: ['192.168.', '10.0.', '172.16.'], // Common local network ranges
            apiUrl: 'http://192.168.95.192:8000'
        }
    };
    
    // Detect current environment
    function detectEnvironment() {
        for (const [envName, config] of Object.entries(environments)) {
            for (const domain of config.domains) {
                if (domain.endsWith('.') && hostname.startsWith(domain)) {
                    return envName;
                }
                if (hostname === domain) {
                    return envName;
                }
            }
        }
        return 'development'; // Default fallback
    }
    
    const currentEnv = detectEnvironment();
    const config = environments[currentEnv];
    
    return {
        environment: currentEnv,
        apiUrl: config.apiUrl,
        isProduction: currentEnv === 'production',
        isDevelopment: currentEnv === 'development',
        
        // Debug info
        debug: {
            hostname: hostname,
            protocol: protocol,
            detectedEnv: currentEnv,
            availableEnvs: Object.keys(environments)
        }
    };
})();

// Log configuration in development
if (!window.AppConfig.isProduction) {
    console.log('App Configuration:', window.AppConfig);
} 