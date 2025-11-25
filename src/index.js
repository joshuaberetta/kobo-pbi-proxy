/**
 * KoboToolbox Synchronous Export Proxy
 * Proxies requests to Kobo's synchronous export API with simplified permissions.
 * 
 * URL Pattern: /exports/<asset_uid>/<export-settings_uid>/<csv|xlsx>
 */

export default {
  async fetch(request, env, ctx) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return handleCORS();
    }

    try {
      const url = new URL(request.url);
      
      // 1. Load Permissions
      // Permissions are stored in a Worker Secret (PROXY_PERMISSIONS) as a JSON string
      let PERMISSIONS = {};
      try {
        if (env.PROXY_PERMISSIONS) {
          PERMISSIONS = JSON.parse(env.PROXY_PERMISSIONS);
        } else {
          console.warn('PROXY_PERMISSIONS secret is missing.');
        }
      } catch (e) {
        console.error('Failed to parse PROXY_PERMISSIONS:', e);
        return jsonResponse({ error: 'Server Configuration Error' }, 500);
      }

      // 2. Authentication
      // Check header first, then query param (useful for Power BI)
      let apiKey = request.headers.get('X-API-Key');
      if (!apiKey) {
        apiKey = url.searchParams.get('api_key');
      }

      if (!apiKey) {
        return jsonResponse({ error: 'Missing API Key. Provide X-API-Key header or api_key query parameter.' }, 401);
      }

      const userPermissions = PERMISSIONS[apiKey];
      if (!userPermissions) {
        return jsonResponse({ error: 'Invalid API Key' }, 403);
      }

      // 3. Routing
      // Pattern: /exports/<asset_uid>/<export-settings_uid>/<xlsx | csv>
      const pathParts = url.pathname.split('/').filter(p => p); // Remove empty strings
      
      // Expecting: ['exports', 'asset_uid', 'setting_uid', 'format']
      if (pathParts.length === 4 && pathParts[0] === 'exports') {
        const [_, assetUid, settingUid, format] = pathParts;
        return await handleExportRequest(request, env, userPermissions, assetUid, settingUid, format);
      } else if (url.pathname === '/health') {
        return jsonResponse({ status: 'healthy', timestamp: new Date().toISOString() });
      } else {
        return jsonResponse({ 
          error: 'Invalid endpoint', 
          usage: '/exports/<asset_uid>/<export-settings_uid>/<csv|xlsx>' 
        }, 404);
      }

    } catch (error) {
      console.error('Proxy Error:', error);
      return jsonResponse({ error: 'Internal Server Error', details: error.message }, 500);
    }
  }
};

async function handleExportRequest(request, env, permissions, assetUid, settingUid, format) {
  // 1. Validate Format
  if (!['csv', 'xlsx'].includes(format)) {
    return jsonResponse({ error: 'Invalid format. Supported: csv, xlsx' }, 400);
  }

  // 2. Validate Permissions
  const isAllowed = permissions.allowed.some(p => 
    p.asset === assetUid && p.setting === settingUid
  );

  if (!isAllowed) {
    return jsonResponse({ error: 'Access denied for this asset/export setting combination.' }, 403);
  }

  // 3. Construct Upstream URL
  // Default to Kobo Humanitarian if not set, but user snippet used kf.kobotoolbox.org
  const koboBaseUrl = (env.KOBO_BASE_URL || 'https://kf.kobotoolbox.org').replace(/\/$/, '');
  const upstreamUrl = `${koboBaseUrl}/api/v2/assets/${assetUid}/export-settings/${settingUid}/data.${format}`;

  // 4. Fetch from Kobo
  // We need the worker's own Kobo token to authenticate with upstream
  if (!env.KOBO_API_TOKEN) {
    return jsonResponse({ error: 'Server misconfiguration: KOBO_API_TOKEN not set' }, 500);
  }

  const koboResponse = await fetch(upstreamUrl, {
    method: 'GET',
    headers: {
      'Authorization': `Token ${env.KOBO_API_TOKEN}`,
      // Forward user agent or other headers if needed, but usually clean is better
    }
  });

  if (!koboResponse.ok) {
    return jsonResponse({ 
      error: 'Upstream Kobo Error', 
      status: koboResponse.status,
      message: await koboResponse.text() 
    }, koboResponse.status);
  }

  // 5. Stream Response back to client
  // Create a new response with the body stream from Kobo
  const newHeaders = new Headers(koboResponse.headers);
  
  // Ensure CORS is set on the response
  newHeaders.set('Access-Control-Allow-Origin', '*');
  
  // If Kobo doesn't send a filename, we might want to add one, but usually they do.
  // We can optionally override Content-Disposition if needed.

  return new Response(koboResponse.body, {
    status: koboResponse.status,
    headers: newHeaders
  });
}

function handleCORS() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
    }
  });
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*'
    }
  });
}
