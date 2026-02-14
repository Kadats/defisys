<template>
  <div ref="terminalContainer" class="h-full w-full" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

const terminalContainer = ref(null);
let terminal = null;
let fitAddon = null;
let socket = null;
let reconnectTimer = null;

const getWebSocketUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}/ws/logs`;
};

const connectWebSocket = () => {
  if (!terminal) return;

  socket = new WebSocket(getWebSocketUrl());

  socket.onmessage = (event) => {
    terminal.write(`${event.data}\r\n`);
  };

  socket.onclose = () => {
    if (reconnectTimer) return;
    reconnectTimer = window.setInterval(() => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        window.clearInterval(reconnectTimer);
        reconnectTimer = null;
        return;
      }
      connectWebSocket();
    }, 5000);
  };

  socket.onerror = () => {
    socket.close();
  };
};

const resize = () => {
  if (fitAddon) {
    fitAddon.fit();
  }
};

onMounted(() => {
  terminal = new Terminal({
    cursorBlink: true,
    fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    fontSize: 13,
    theme: {
      background: '#000000',
    },
  });

  fitAddon = new FitAddon();
  terminal.loadAddon(fitAddon);

  if (terminalContainer.value) {
    terminal.open(terminalContainer.value);
    resize();
  }

  window.addEventListener('resize', resize);
  connectWebSocket();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize);

  if (reconnectTimer) {
    window.clearInterval(reconnectTimer);
    reconnectTimer = null;
  }

  if (socket) {
    socket.close();
    socket = null;
  }

  if (terminal) {
    terminal.dispose();
    terminal = null;
  }

  fitAddon = null;
});
</script>
