// Service Worker for offline caching and performance optimization
const CACHE_NAME = 'app-cache-v1'
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.ico'
]

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Opened cache:', CACHE_NAME)
        return cache.addAll(STATIC_ASSETS)
      })
      .then(() => self.skipWaiting())
  )
})

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name)
              return caches.delete(name)
            })
        ))
      .then(() => self.clients.claim())
  )
})

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return
  }

  // Skip API requests
  if (event.request.url.includes('/api/')) {
    return
  }

  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          // Return cached response and update cache in background
          const fetchPromise = fetch(event.request)
            .then((networkResponse) => {
              if (networkResponse && networkResponse.status === 200) {
                const responseClone = networkResponse.clone()
                caches.open(CACHE_NAME)
                  .then((cache) => {
                    cache.put(event.request, responseClone)
                  })
              }
              return networkResponse
            })
            .catch(() => 
              // Network request failed, cached response is sufficient
               null
            )

          return cachedResponse
        }

        // No cached response, fetch from network
        return fetch(event.request)
          .then((networkResponse) => {
            // Cache the response for future use
            if (networkResponse && networkResponse.status === 200) {
              const responseClone = networkResponse.clone()
              caches.open(CACHE_NAME)
                .then((cache) => {
                  cache.put(event.request, responseClone)
                })
            }
            return networkResponse
          })
          .catch(() => {
            // Network request failed and no cache available
            // Return offline page for HTML requests
            if (event.request.destination === 'document') {
              return caches.match('/index.html')
            }
            return new Response('Offline', { status: 503 })
          })
      })
  )
})

// Background sync for offline actions (optional enhancement)
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync())
  }
})

async function doBackgroundSync() {
  // Implement background sync logic here
  console.log('[SW] Background sync triggered')
}

// Push notifications (optional enhancement)
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json()
    event.waitUntil(
      self.registration.showNotification(data.title, {
        body: data.body,
        icon: '/icon-192.png',
        badge: '/badge-72.png'
      })
    )
  }
})
