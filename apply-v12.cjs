const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

if (process.env.DEPLOYBRIDGE_APPLY_V12 === '1' && process.env.DEPLOYBRIDGE_PATCH_APPLIED !== '1') {
  process.env.DEPLOYBRIDGE_PATCH_APPLIED = '1';
  const root = __dirname;
  const patchDir = path.join(root, 'patch12');
  const target = path.join(root, '.deploybridge', 'deploybridge-v1');
  const expected = 'c0c09db00374980de6c33120f2776a9753ceea6c2e255dd944ce805944165f42';
  const chunks = fs.readdirSync(patchDir)
    .filter((name) => /^chunk_\d+$/.test(name))
    .sort();

  if (chunks.length !== 6) throw new Error(`DeployBridge v1.2 patch: expected 6 chunks, found ${chunks.length}`);
  if (!fs.existsSync(target)) throw new Error(`DeployBridge v1.2 patch: target missing: ${target}`);

  const encoded = chunks.map((name) => fs.readFileSync(path.join(patchDir, name), 'utf8')).join('').replace(/\s+/g, '');
  const zip = Buffer.from(encoded, 'base64');
  const digest = crypto.createHash('sha256').update(zip).digest('hex');
  if (digest !== expected) throw new Error(`DeployBridge v1.2 patch checksum mismatch: ${digest}`);

  const tempZip = '/tmp/deploybridge-v1.2-patch.zip';
  fs.writeFileSync(tempZip, zip);
  const unzip = spawnSync('unzip', ['-oq', tempZip, '-d', target], { stdio: 'inherit' });
  if (unzip.status !== 0) throw new Error(`DeployBridge v1.2 patch unzip failed with status ${unzip.status}`);

  const pkg = JSON.parse(fs.readFileSync(path.join(target, 'package.json'), 'utf8'));
  if (pkg.version !== '1.2.0') throw new Error(`DeployBridge v1.2 patch version check failed: ${pkg.version}`);
  console.log(`[DeployBridge] v1.2.0 patch verified and applied (${digest})`);
}
