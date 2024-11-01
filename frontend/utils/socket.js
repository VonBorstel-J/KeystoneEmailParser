// frontend/utils/socket.js
import { io } from 'socket.io-client';

const socket = io('http://localhost:5000', {
  path: '/socket.io',
  transports: ['websocket', 'polling']
});

// Event listener for socket connection errors
socket.on('connect_error', (error) => {
  console.error('Socket connection error:', error);
  // Here, you could potentially add more user-facing error handling like a dispatch or notification
});

// Event listener for socket reconnection attempts
socket.on('reconnect_attempt', (attemptNumber) => {
  console.warn(`Reconnection attempt #${attemptNumber}`);
});

// Event listener for successful reconnection
socket.on('reconnect', (attemptNumber) => {
  console.info(`Reconnected successfully after ${attemptNumber} attempt(s)`);
});

// Event listener for connection establishment
socket.on('connect', () => {
  console.info('Socket connection established successfully');
});

// Event listener for disconnection
socket.on('disconnect', (reason) => {
  console.warn(`Socket disconnected: ${reason}`);
  // Optionally, handle reconnection logic here if you want a specific response on disconnection
});

export default socket;
