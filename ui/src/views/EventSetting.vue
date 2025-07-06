<template>
  <div class="event-setting">
    <h1>{{ $t('eventSetting.title') }}</h1>
    <div class="event-menu">
      <div v-for="(item, key) in menuItems" :key="key" class="event-menu-item">
        <router-link :to="'/event-setting/' + key">
          {{ $t('eventSetting.menu.' + key) }}
        </router-link>
      </div>
    </div>
    <router-view></router-view>
  </div>
</template>

<script>
export default {
  name: 'EventSetting',
  data() {
    return {
      menuItems: {
        basic: 'basic',
        event: 'event',
        notification: 'notification',
        schedule: 'schedule',
        temperature: 'temperature',
        face: 'face',
        license: 'license',
        fire: 'fire',
        intrusion: 'intrusion',
        loitering: 'loitering',
        violence: 'violence',
        fall: 'fall',
        crowd: 'crowd',
        smoke: 'smoke',
        mask: 'mask',
        social: 'social',
        queue: 'queue',
        parking: 'parking',
        speed: 'speed',
        direction: 'direction',
        zone: 'zone',
        line: 'line',
        count: 'count',
        density: 'density',
        flow: 'flow',
        tracking: 'tracking',
        alert: 'alert',
        report: 'report',
        export: 'export',
        import: 'import',
        backup: 'backup',
        restore: 'restore',
        log: 'log',
        help: 'help',
        about: 'about'
      }
    }
  }
}
</script>

<style scoped>
.event-setting {
  padding: 20px;
}

.event-menu {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
  justify-content: flex-start;
  align-items: center;
}

.event-menu-item {
  padding: 10px 20px;
  background-color: #f5f5f5;
  border-radius: 5px;
  text-align: center;
}

.event-menu-item a {
  text-decoration: none;
  color: #333;
  font-size: 14px;
  white-space: nowrap;
}

.event-menu-item a:hover {
  color: #409EFF;
}
</style> 