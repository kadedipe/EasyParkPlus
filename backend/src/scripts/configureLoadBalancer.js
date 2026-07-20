// parking-management/backend/src/scripts/configureLoadBalancer.js
import { exec } from 'child_process';
import fs from 'fs';
import { promisify } from 'util';

const execAsync = promisify(exec);

class LoadBalancerConfig {
  constructor() {
    this.configPath = '/etc/nginx/nginx.conf';
    this.servers = [];
    this.healthChecks = [];
  }

  async configure() {
    console.log('⚙️ Configuring Load Balancer...\n');

    // 1. Detect available servers
    await this.detectServers();

    // 2. Configure health checks
    await this.configureHealthChecks();

    // 3. Update nginx configuration
    await this.updateNginxConfig();

    // 4. Validate configuration
    await this.validateConfig();

    // 5. Reload nginx
    await this.reloadNginx();

    console.log('\n✅ Load balancer configuration complete!');
  }

  async detectServers() {
    console.log('🔍 Detecting servers...');
    
    // Check backend servers
    const backendPorts = [5000, 5001, 5002];
    for (const port of backendPorts) {
      try {
        await execAsync(`nc -zv localhost ${port}`);
        this.servers.push({
          type: 'backend',
          port: port,
          status: 'healthy',
        });
        console.log(`  ✅ Backend server found on port ${port}`);
      } catch (error) {
        console.log(`  ❌ No backend server on port ${port}`);
      }
    }

    // Check frontend servers
    const frontendPorts = [80, 8080, 8081];
    for (const port of frontendPorts) {
      try {
        await execAsync(`nc -zv localhost ${port}`);
        this.servers.push({
          type: 'frontend',
          port: port,
          status: 'healthy',
        });
        console.log(`  ✅ Frontend server found on port ${port}`);
      } catch (error) {
        console.log(`  ❌ No frontend server on port ${port}`);
      }
    }
  }

  async configureHealthChecks() {
    console.log('🔍 Configuring health checks...');
    
    for (const server of this.servers) {
      const healthCheck = {
        server: server,
        endpoint: '/health',
        interval: 30,
        timeout: 5,
        retries: 3,
      };
      this.healthChecks.push(healthCheck);
      console.log(`  ✅ Health check configured for ${server.type} on port ${server.port}`);
    }
  }

  async updateNginxConfig() {
    console.log('📝 Updating nginx configuration...');
    
    const config = this.generateNginxConfig();
    
    // Backup existing config
    const backupPath = `${this.configPath}.backup.${Date.now()}`;
    if (fs.existsSync(this.configPath)) {
      fs.copyFileSync(this.configPath, backupPath);
      console.log(`  ✅ Backup created: ${backupPath}`);
    }

    // Write new config
    fs.writeFileSync(this.configPath, config);
    console.log(`  ✅ Configuration written to ${this.configPath}`);
  }

  generateNginxConfig() {
    const backendServers = this.servers
      .filter(s => s.type === 'backend')
      .map(s => `server localhost:${s.port};`)
      .join('\n    ');

    const frontendServers = this.servers
      .filter(s => s.type === 'frontend')
      .map(s => `server localhost:${s.port};`)
      .join('\n    ');

    return `
# Load Balancer Configuration
# Generated at ${new Date().toISOString()}

events {
    worker_connections 1024;
    multi_accept on;
}

http {
    # Upstream backend servers
    upstream backend_servers {
        # Load balancing algorithm
        least_conn;
        
        # Servers
        ${backendServers}
        
        # Health check
        keepalive 32;
    }

    # Upstream frontend servers
    upstream frontend_servers {
        ${frontendServers}
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # Include server configuration
    include /etc/nginx/conf.d/*.conf;
}
`;
  }

  async validateConfig() {
    console.log('🔍 Validating configuration...');
    
    try {
      await execAsync('nginx -t');
      console.log('  ✅ Configuration validation passed');
    } catch (error) {
      console.log(`  ❌ Configuration validation failed: ${error.message}`);
      throw error;
    }
  }

  async reloadNginx() {
    console.log('🔄 Reloading nginx...');
    
    try {
      await execAsync('nginx -s reload');
      console.log('  ✅ Nginx reloaded successfully');
    } catch (error) {
      console.log(`  ❌ Nginx reload failed: ${error.message}`);
      throw error;
    }
  }

  async getLoadBalancerStatus() {
    try {
      const { stdout } = await execAsync('curl -s http://localhost/lb-status');
      return JSON.parse(stdout);
    } catch (error) {
      return { status: 'unavailable', error: error.message };
    }
  }
}

// Run configuration
const config = new LoadBalancerConfig();
config.configure().catch(console.error);