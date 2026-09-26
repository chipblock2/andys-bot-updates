import { json } from "../src/http.js";
export default async function handler(req,res){
  return json(res,200,{ok:true,service:"deploybridge-ai",version:"1.2.0",auth:"oauth",provider:"vercel-connect+rest"});
}
