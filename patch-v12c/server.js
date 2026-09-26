import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import mcp from "./api/mcp.js";
import health from "./api/health.js";
import oauthRegister from "./api/oauth-register.js";
import oauthAuthorize from "./api/oauth-authorize.js";
import oauthCallback from "./api/oauth-callback.js";
import oauthToken from "./api/oauth-token.js";
import wellAuth from "./api/well-known-auth.js";
import wellResource from "./api/well-known-resource.js";
import oauthUserinfo from "./api/oauth-userinfo.js";
import openaiAppsChallenge from "./api/openai-apps-challenge.js";
const root=path.dirname(fileURLToPath(import.meta.url));
const handlers={"/mcp":mcp,"/health":health,"/oauth/register":oauthRegister,"/oauth/authorize":oauthAuthorize,"/oauth/callback":oauthCallback,"/oauth/token":oauthToken,"/oauth/userinfo":oauthUserinfo,"/.well-known/oauth-authorization-server":wellAuth,"/.well-known/oauth-protected-resource":wellResource,"/.well-known/oauth-protected-resource/mcp":wellResource,"/.well-known/openai-apps-challenge":openaiAppsChallenge};
const staticFiles={"/":"index.html","/privacy.html":"privacy.html","/terms.html":"terms.html","/support.html":"support.html"};
const server=http.createServer(async(req,res)=>{
  const pathname=new URL(req.url,"http://localhost").pathname;
  if(handlers[pathname]){let raw="";for await(const chunk of req)raw+=chunk;if(raw){const type=req.headers["content-type"]||"";req.body=type.includes("application/json")?JSON.parse(raw):raw;}return handlers[pathname](req,res);}
  if(staticFiles[pathname]){res.setHeader("content-type","text/html; charset=utf-8");return res.end(fs.readFileSync(path.join(root,staticFiles[pathname])));}
  res.statusCode=404;res.end("Not found");
});
server.listen(process.env.PORT||3000,()=>console.log(`DeployBridge dev server on http://localhost:${process.env.PORT||3000}`));
