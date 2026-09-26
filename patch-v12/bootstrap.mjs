import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";

const root=process.cwd();
const patchDir=path.join(root,"patch-v12");
const target=path.join(root,".deploybridge","deploybridge-v1");
const expected="aacee8e91e8ecd8c7995b4cd28c99be1a6c5368ebd4e8cda99d263194303e13d";

if(fs.existsSync(patchDir)&&fs.existsSync(target)){
  const names=fs.readdirSync(patchDir).filter(n=>/^chunk_\d+$/.test(n)).sort();
  if(names.length!==3)throw new Error("DeployBridge v1.2 patch chunks missing");
  const encoded=names.map(n=>fs.readFileSync(path.join(patchDir,n),"utf8").trim()).join("");
  const archive=Buffer.from(encoded,"base64");
  const actual=crypto.createHash("sha256").update(archive).digest("hex");
  if(actual!==expected)throw new Error(`DeployBridge v1.2 patch checksum mismatch: ${actual}`);
  const tmp="/tmp/deploybridge-v12-patch.tgz";
  fs.writeFileSync(tmp,archive);
  execFileSync("tar",["-xzf",tmp,"-C",target],{stdio:"inherit"});
  console.log("DeployBridge v1.2 review patch verified and applied");
}
