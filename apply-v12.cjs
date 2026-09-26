const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

function sha256(buf) { return crypto.createHash('sha256').update(buf).digest('hex'); }

if (process.env.DEPLOYBRIDGE_APPLY_V12 === '1' && process.env.DEPLOYBRIDGE_PATCH_APPLIED !== '1') {
  process.env.DEPLOYBRIDGE_PATCH_APPLIED = '1';
  const root = __dirname;
  const patchDir = path.join(root, 'patch12');
  const target = path.join(root, '.deploybridge', 'deploybridge-v1');
  const expectedPatch = 'c0c09db00374980de6c33120f2776a9753ceea6c2e255dd944ce805944165f42';
  const chunks = fs.readdirSync(patchDir).filter((name) => /^chunk_\d+$/.test(name)).sort();

  if (chunks.length !== 6) throw new Error(`DeployBridge v1.2 patch: expected 6 chunks, found ${chunks.length}`);
  if (!fs.existsSync(target)) throw new Error(`DeployBridge v1.2 patch: target missing: ${target}`);

  const encoded = chunks.map((name) => fs.readFileSync(path.join(patchDir, name), 'utf8')).join('').replace(/\s+/g, '');
  const zip = Buffer.from(encoded, 'base64');
  const patchDigest = sha256(zip);
  if (patchDigest !== expectedPatch) throw new Error(`DeployBridge v1.2 patch checksum mismatch: ${patchDigest}`);

  const tempZip = '/tmp/deploybridge-v1.2-patch.zip';
  fs.writeFileSync(tempZip, zip);
  const unzip = spawnSync('unzip', ['-oq', tempZip, '-d', target], { stdio: 'inherit' });
  if (unzip.status !== 0) throw new Error(`DeployBridge v1.2 patch unzip failed with status ${unzip.status}`);

  const healthSource = path.join(root, 'hotfix12', 'health.js');
  const expectedHealth = 'f6c352414800cc17c75e6e1973814e57f1201970c72f9ef72f62e8e4762b1031';
  const healthBytes = fs.readFileSync(healthSource);
  const healthDigest = sha256(healthBytes);
  if (healthDigest !== expectedHealth) throw new Error(`DeployBridge v1.2 health checksum mismatch: ${healthDigest}`);
  fs.copyFileSync(healthSource, path.join(target, 'api', 'health.js'));

  const pkg = JSON.parse(fs.readFileSync(path.join(target, 'package.json'), 'utf8'));
  if (pkg.version !== '1.2.0') throw new Error(`DeployBridge v1.2 patch version check failed: ${pkg.version}`);
  console.log(`[DeployBridge] v1.2.0 patch verified and applied (${patchDigest})`);
  console.log(`[DeployBridge] v1.2.0 health hotfix verified (${healthDigest})`);

  const isServerRuntime = Boolean(process.argv[1] && /server\.js$/.test(process.argv[1]));
  if (process.env.PORT && isServerRuntime) {
    const port = process.env.PORT;
    const base = `http://127.0.0.1:${port}`;
    setTimeout(async () => {
      try {
        const health = await fetch(`${base}/health`);
        const healthJson = await health.json();
        if (health.status !== 200 || healthJson.version !== '1.2.0') throw new Error(`health ${health.status} version=${healthJson.version}`);

        const auth = await fetch(`${base}/.well-known/oauth-authorization-server`);
        const authJson = await auth.json();
        if (auth.status !== 200 || !authJson.authorization_endpoint || !authJson.token_endpoint) throw new Error(`oauth metadata ${auth.status}`);

        const resource = await fetch(`${base}/.well-known/oauth-protected-resource/mcp`);
        const resourceJson = await resource.json();
        if (resource.status !== 200 || !Array.isArray(resourceJson.authorization_servers)) throw new Error(`resource metadata ${resource.status}`);

        const challenge = await fetch(`${base}/.well-known/openai-apps-challenge`);
        const challengeExpected = process.env.OPENAI_APPS_CHALLENGE ? 200 : 404;
        if (challenge.status !== challengeExpected) throw new Error(`challenge ${challenge.status}, expected ${challengeExpected}`);

        for (const pathname of ['/privacy.html','/terms.html','/support.html']) {
          const page = await fetch(`${base}${pathname}`);
          if (page.status !== 200) throw new Error(`${pathname} ${page.status}`);
        }

        const mcp = await fetch(`${base}/mcp`, { method: 'POST', headers: {'content-type':'application/json'}, body: '{}' });
        if (mcp.status !== 401) throw new Error(`unauthenticated MCP ${mcp.status}, expected 401`);
        console.log('[DeployBridge smoke] PASS health/oauth/resource/legal/challenge/mcp-auth');
      } catch (error) {
        console.error(`[DeployBridge smoke] FAIL ${error?.message || error}`);
        process.exit(1);
      }
    }, 5000).unref();
  }
}
