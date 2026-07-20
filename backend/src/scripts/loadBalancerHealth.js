// parking-management/backend/src/scripts/loadBalancerHealth.js
import axios from 'axios';

class LoadBalancerHealth {
  constructor() {
    this.servers = [];
    this.healthHistory = [];
  }

  async checkHealth() {
    console.log('🏥 Checking Load Balancer Health...\n');

    // Check each server
    for (const server of this.getServerList()) {
      await this.checkServerHealth(server);
    }

    // Check overall health
    const overallHealth = this.getOverallHealth();

    // Generate report
    this.generateReport(overallHealth);

    return overallHealth;
  }

  getServerList() {
    // This would typically come from configuration
    return [
      { id: 'backend-1', host: 'localhost', port: 5000 },
      { id: 'backend-2', host: 'localhost', port: 5001 },
      { id: 'backend-3', host: 'localhost', port: 5002 },
      { id: 'frontend-1', host: 'localhost', port: 80 },
      { id: 'frontend-2', host: 'localhost', port: 8080 },
    ];
  }

  async checkServerHealth(server) {
    try {
      const start = Date.now();
      const response = await axios.get(`http://${server.host}:${server.port}/health`, {
        timeout: 5000,
        validateStatus: false,
      });
      const responseTime = Date.now() - start;

      const health = {
        server: server.id,
        status: response.status === 200 ? 'healthy' : 'unhealthy',
        responseTime: responseTime,
        timestamp: new Date().toISOString(),
        details: response.data,
      };

      this.servers.push(health);
      this.healthHistory.push(health);

      console.log(`  ${health.status === 'healthy' ? '✅' : '❌'} ${server.id}: ${responseTime}ms`);
    } catch (error) {
      const health = {
        server: server.id,
        status: 'unreachable',
        responseTime: 0,
        timestamp: new Date().toISOString(),
        error: error.message,
      };

      this.servers.push(health);
      this.healthHistory.push(health);

      console.log(`  ❌ ${server.id}: Unreachable`);
    }
  }

  getOverallHealth() {
    const healthy = this.servers.filter(s => s.status === 'healthy');
    const unhealthy = this.servers.filter(s => s.status !== 'healthy');
    const total = this.servers.length;

    return {
      status: unhealthy.length === 0 ? 'healthy' : 'degraded',
      healthyCount: healthy.length,
      unhealthyCount: unhealthy.length,
      total: total,
      healthPercentage: (healthy.length / total * 100).toFixed(2),
      servers: this.servers,
      timestamp: new Date().toISOString(),
    };
  }

  generateReport(health) {
    console.log('\n📊 Load Balancer Health Report:');
    console.log('═'.repeat(50));
    console.log(`Status: ${health.status.toUpperCase()}`);
    console.log(`Healthy: ${health.healthyCount}/${health.total}`);
    console.log(`Health Percentage: ${health.healthPercentage}%`);
    console.log('═'.repeat(50));

    // Check if any servers are unhealthy
    if (health.unhealthyCount > 0) {
      console.log('\n⚠️ Unhealthy Servers:');
      health.servers
        .filter(s => s.status !== 'healthy')
        .forEach(s => {
          console.log(`  ❌ ${s.server}: ${s.status} - ${s.error || 'No details'}`);
        });

      console.log('\n💡 Recommendations:');
      if (health.unhealthyCount > health.total / 2) {
        console.log('  - Critical: More than 50% of servers are unhealthy');
        console.log('  - Check server logs and resources');
      } else {
        console.log('  - Review health check configuration');
        console.log('  - Check server resources (CPU, Memory, Disk)');
      }
    } else {
      console.log('\n✅ All servers are healthy!');
    }
  }

  async monitorHealth(interval = 60000) {
    console.log(`🔄 Monitoring load balancer health every ${interval/1000} seconds...\n`);

    await this.checkHealth();

    setInterval(async () => {
      console.clear();
      await this.checkHealth();
    }, interval);
  }
}

// Run health check
const health = new LoadBalancerHealth();
health.monitorHealth(30000).catch(console.error);