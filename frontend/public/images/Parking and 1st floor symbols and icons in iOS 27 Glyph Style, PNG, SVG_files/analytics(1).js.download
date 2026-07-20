(function() {
  class WidgetAnalytics {
    constructor() {
      if (window.widgetAnalytics) {
        console.warn('Widget Analytics already initialized');
        return window.widgetAnalytics;
      }
      
      const isDev = window.location.hostname === 'localhost' || window.location.hostname.includes('local');
      this.endpoint = isDev 
        ? 'http://localhost:3000/api/widget-analytics'
        : 'https://icons8-tools.icons8.com/api/widget-analytics';
      
      this.sessionData = this.collectSessionData();
      this.eventListeners = new Map();
      this.setupEventListeners();
      this.log('Initialized', 'info', this.sessionData);
    }

    log(message, type = 'info', data = null) {
      const styles = {
        info: 'background: #2196F3; color: white; padding: 2px 5px; border-radius: 3px;',
        error: 'background: #f44336; color: white; padding: 2px 5px; border-radius: 3px;',
        success: 'background: #4CAF50; color: white; padding: 2px 5px; border-radius: 3px;',
        event: 'background: #9C27B0; color: white; padding: 2px 5px; border-radius: 3px;'
      };
    }

    collectSessionData() {
      return {
        browser: {
          language: navigator.language,
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          screenResolution: `${window.screen.width}x${window.screen.height}`,
          deviceType: this.getDeviceType(),
          os: this.getOS()
        },
        page: {
          url: window.location.href,
          path: window.location.pathname,
          referrer: this.getReferrer(),
          utmParams: this.getUtmParams()
        },
        user: {
          loginStatus: this.getLoginStatus(),
          accountType: this.getAccountType()
        },
        timestamp: new Date().toISOString()
      };
    }

    getDeviceType() {
      const ua = navigator.userAgent;
      if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) {
        return 'tablet';
      }
      if (/Mobile|Android|iP(hone|od)|IEMobile|BlackBerry|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(obi|ini)/.test(ua)) {
        return 'mobile';
      }
      return 'desktop';
    }

    getOS() {
      const userAgent = window.navigator.userAgent;
      const platform = window.navigator.platform;
      const macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'];
      const windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'];
      const iosPlatforms = ['iPhone', 'iPad', 'iPod'];

      if (macosPlatforms.indexOf(platform) !== -1) {
        return 'MacOS';
      } else if (iosPlatforms.indexOf(platform) !== -1) {
        return 'iOS';
      } else if (windowsPlatforms.indexOf(platform) !== -1) {
        return 'Windows';
      } else if (/Android/.test(userAgent)) {
        return 'Android';
      } else if (/Linux/.test(platform)) {
        return 'Linux';
      }
      return 'Unknown';
    }

    getReferrer() {
      const cookies = document.cookie.split(';');
      const refCookie = cookies.find(c => c.trim().startsWith('i8-referral-code='));
      if (refCookie) {
        return decodeURIComponent(refCookie.split('=')[1]);
      }
      return document.referrer;
    }

    getUtmParams() {
      const urlParams = new URLSearchParams(window.location.search);
      return {
        source: urlParams.get('utm_source'),
        medium: urlParams.get('utm_medium'),
        campaign: urlParams.get('utm_campaign'),
        term: urlParams.get('utm_term'),
        content: urlParams.get('utm_content')
      };
    }

    getLoginStatus() {
      try {
        return window.__NUXT__?.pinia?.['auth-v3']?.user ? 'logged_in' : 'guest';
      } catch {
        return 'unknown';
      }
    }

    getAccountType() {
      try {
        const user = window.__NUXT__?.pinia?.['auth-v3']?.user;
        return user?.isPaid ? 'paid' : 'free';
      } catch {
        return 'unknown';
      }
    }

    setupEventListeners() {
      const eventTypes = ['widgetView', 'widgetClick', 'widgetClose'];
      
      eventTypes.forEach(eventType => {
        if (this.eventListeners.has(eventType)) {
          window.removeEventListener(eventType, this.eventListeners.get(eventType));
        }
        
        const listener = (e) => {
          const detail = {
            ...e.detail,
            title: e.detail.title || document.querySelector('.i8-widget__title')?.textContent || '',
            subtitle: document.querySelector('.i8-widget__subtitle')?.textContent || '',
            buttonName: e.detail.buttonName || document.querySelector('.i8-widget__btn')?.textContent || '',
            buttonLink: e.detail.buttonLink || document.querySelector('.i8-widget__btn')?.getAttribute('data-link') || ''
          };
          
          this.handleEvent(eventType, detail);
        };
        
        this.eventListeners.set(eventType, listener);
        
        window.addEventListener(eventType, listener);
      });
      
    }

    async handleEvent(type, data) {
      
      try {
        const payload = {
          type,
          data,
          sessionData: this.sessionData
        };


        if (window.analyticsProxy && typeof window.analyticsProxy.sendEvent === 'function') {
          const result = await window.analyticsProxy.sendEvent(payload);
        } else {
          const response = await fetch(this.endpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload),
            keepalive: true
          });

          if (!response.ok) {
            throw new Error(`Failed to send analytics data: ${response.status}`);
          }
        }
      } catch (error) {
        console.error('Error processing event:', error);
      }
    }

    async sendBatch(events) {
      this.log('Sending batch events', 'info', events);
      try {
        const payload = {
          events,
          sessionData: this.sessionData
        };

        if (window.analyticsProxy && typeof window.analyticsProxy.sendBatch === 'function') {
          const result = await window.analyticsProxy.sendBatch(payload);
        } else {
          const response = await fetch(`${this.endpoint}/batch`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload),
            keepalive: true
          });

          if (!response.ok) {
            throw new Error('Failed to send batch analytics data');
          }
        }
        
        this.log('Batch sent successfully', 'success');
      } catch (error) {
        this.log('Batch error', 'error', error);
      }
    }
  }

  window.widgetAnalytics = new WidgetAnalytics();
})();