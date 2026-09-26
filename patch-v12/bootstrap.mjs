import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.dirname(here);
const target=path.join(root,".deploybridge","deploybridge-v1");

function applyPatch(dir, expected, label) {
  if(!fs.existsSync(dir)||!fs.existsSync(target)) return;
  const names=fs.readdirSync(dir).filter(n=>/^chunk_\d+$/.test(n)).sort();
  if(!names.length) throw new Error(`${label} chunks missing`);
  const encoded=names.map(n=>fs.readFileSync(path.join(dir,n),"utf8").trim()).join("");
  const archive=Buffer.from(encoded,"base64");
  const actual=crypto.createHash("sha256").update(archive).digest("hex");
  if(actual!==expected) throw new Error(`${label} checksum mismatch: ${actual}`);
  const tmp=`/tmp/${label.replace(/[^a-z0-9]+/gi,"-").toLowerCase()}.tgz`;
  fs.writeFileSync(tmp,archive);
  execFileSync("tar",["-xzf",tmp,"-C",target],{stdio:"inherit"});
  console.log(`${label} verified and applied`);
}

applyPatch(here,"aacee8e91e8ecd8c7995b4cd28c99be1a6c5368ebd4e8cda99d263194303e13d","DeployBridge v1.2 review patch");
applyPatch(path.join(root,"patch-v12b"),"69082e208122761b82bca1ec1afca75e2b5e403c7a0d64db4d48d183cca93750","DeployBridge v1.2 health patch");
applyPatch(path.join(root,"patch-v12c"),"75bd54f682bb85cd5d34421583b2521979a13c484353c3c647f76460bf379dfb","DeployBridge v1.2 route patch");
