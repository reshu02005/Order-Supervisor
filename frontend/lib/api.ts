const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
export async function request<T>(path:string,body?:unknown):Promise<T>{
 const r=await fetch(API+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail));return d;
}
