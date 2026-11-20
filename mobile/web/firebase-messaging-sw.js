
importScripts(
  'https://www.gstatic.com/firebasejs/11.0.0/firebase-app-compat.js'
);
importScripts(
  'https://www.gstatic.com/firebasejs/11.0.0/firebase-messaging-compat.js'
);

firebase.initializeApp({
  apiKey: 'AIzaSyDaA-s3Ita4J12MG2dQZyOpCZG6OU0b-Mw',
  authDomain: 'roadsafe-dc411.firebaseapp.com',
  projectId: 'roadsafe-dc411',
  storageBucket: 'roadsafe-dc411.firebasestorage.app',
  messagingSenderId: '696080346634',
  appId: '1:696080346634:web:90e061fca3216d3f8db9f3',
  measurementId: 'G-V4SCHQKQHF'
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  console.log(
    '[firebase-messaging-sw.js] Background message:',
    payload
  );

  const title =
    payload.notification?.title || 'Pharos Safety Alert';

  const options = {
    body:
      payload.notification?.body ||
      'You have a new safety notification.',
    icon: '/icons/Icon-192.png',
    data: payload.data || {}
  };

  self.registration.showNotification(title, options);
});
