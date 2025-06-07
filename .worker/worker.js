addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  const path = url.pathname

  let response

  if (path === '/refresh-map') {
    response = await refreshMapCache()
  } else {
    response = await mirrorToRepo(path, request)
  }

  if (isJsonPath(path)) {
    const newHeaders = new Headers(response.headers)
    newHeaders.set('Content-Type', 'application/json')
    response = new Response(response.body, {
      status: response.status,
      headers: newHeaders
    })
  }

  return response
}

function isJsonPath(path) {
  return path.endsWith('.json') || path === '/map.json' || path === '//map.json'
}

async function mirrorToRepo(path, request) {
  const githubUrl = `https://raw.githubusercontent.com/ErisPulse/ErisPulse-ModuleRepo/main${path}`

  let response = await fetch(githubUrl, {
    cf: {
      cacheEverything: true,
      cacheTtl: 14400 // 缓存 4 小时
    }
  })

  if (response.status === 404 && !path.endsWith('.zip')) {
    const zipResponse = await fetch(`${githubUrl}.zip`, {
      cf: {
        cacheEverything: true,
        cacheTtl: 14400
      }
    })
    response = zipResponse
  }

  return response
}

async function refreshMapCache() {
  const cacheUrl = 'https://raw.githubusercontent.com/ErisPulse/ErisPulse-ModuleRepo/main/map.json'

  const cacheKey = new Request(cacheUrl)
  const cache = caches.default

  await cache.delete(cacheKey)

  const response = await fetch(cacheUrl, {
    cf: {
      cacheEverything: true,
      cacheTtl: 14400
    }
  })

  return new Response(JSON.stringify({ message: 'GitHub map.json cache refreshed' }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store'
    }
  })
}