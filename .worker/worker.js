addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  const path = url.pathname

  return mirrorToRepo(path, request)
}

async function mirrorToRepo(path, request) {
  const githubUrl = `https://raw.githubusercontent.com/ErisPulse/ErisPulse-ModuleRepo/main${path}`

  const response = await fetch(githubUrl, {
    cf: {
      cacheEverything: true,
      cacheTtl: 86400 // 缓存 24 小时
    }
  })

  if (response.status === 404 && !path.endsWith('.zip')) {
    const zipResponse = await fetch(`${githubUrl}.zip`, {
      cf: {
        cacheEverything: true,
        cacheTtl: 86400
      }
    })
    return zipResponse
  }

  return response
}
