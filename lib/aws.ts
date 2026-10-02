import { AwsClient } from 'aws4fetch';
import { env } from 'cloudflare:workers';
export const REGION = 'us-east-1';
const config = () => env as unknown as Record<string,string>;
export const bucket = () => config().MEDIA_BUCKET;
export const table = () => config().MATCH_TABLE;
function aws(){const c=config();if(!c.MEDIA_ACCESS_KEY || !c.MEDIA_SECRET_KEY)throw new Error('Media service is not configured.');return new AwsClient({accessKeyId:c.MEDIA_ACCESS_KEY,secretAccessKey:c.MEDIA_SECRET_KEY,region:REGION,retries:3});}
export async function db(action:string, body:Record<string,unknown>){const r=await aws().fetch(`https://dynamodb.${REGION}.amazonaws.com/`,{method:'POST',headers:{'content-type':'application/x-amz-json-1.0','x-amz-target':`DynamoDB_20120810.${action}`},body:JSON.stringify({TableName:table(),...body})});const d=await r.json() as Record<string,any>;if(!r.ok)throw new Error(String(d.__type||'Database unavailable'));return d;}
export async function scan(body:Record<string,unknown>){const items:Record<string,any>[]=[];let cursor:unknown;do{const d=await db('Scan',{...body,...(cursor?{ExclusiveStartKey:cursor}:{})});items.push(...(d.Items||[]));cursor=d.LastEvaluatedKey;}while(cursor);return {Items:items};}
export type Event = {id:string,time:number,start:number,end:number,kind:string,confidence:number,evidence:string,included:boolean,manual?:boolean,verified?:boolean};
export type RenderMusic = {id:string,title:string,artist:string,youtube:string,source:string,license:string,licenseUrl:string,revision:number,credits:string};
export type Match = {id:string,owner:string,title:string,created:number,status:string,note?:string,error?:string,filename:string,mime:string,size:number,key:string,uploadId?:string,recording?:boolean,parts?:number,duration?:number,analyzed?:number,events:Event[],revision:number,length:number,labels:boolean,music?:string,renderMusic?:RenderMusic,reelKey?:string,reelDuration?:number,metrics?:Record<string,unknown>,attempts?:number,analysisComplete?:boolean};
export function unpack(i:Record<string,any>):Match{return {...JSON.parse(i.doc.S),status:i.stage.S};}
export async function get(id:string){const d=await db('GetItem',{Key:{id:{S:id}},ConsistentRead:true});return d.Item?unpack(d.Item):null;}
export async function put(m:Match, condition?:string,values?:Record<string,unknown>){return db('PutItem',{Item:{id:{S:m.id},owner:{S:m.owner},stage:{S:m.status},doc:{S:JSON.stringify(m)},lease:{N:'0'},revision:{N:String(m.revision)},updated:{N:String(Date.now())}},...(condition?{ConditionExpression:condition,ExpressionAttributeValues:values}:{})});}
export async function owned(id:string,owner:string){const m=await get(id);if(!m || m.owner!==owner)throw new Error('Match not found.');return m;}
export function objectUrl(key:string,query=''){return `https://${bucket()}.s3.${REGION}.amazonaws.com/${key.split('/').map(encodeURIComponent).join('/')}${query}`;}
export async function s3(key:string,query:string,init:RequestInit={}){const r=await aws().fetch(objectUrl(key,query),init);if(!r.ok)throw new Error(`Storage request failed (${r.status}).`);return r;}
export async function signed(key:string,method='GET',query=''){const url=new URL(objectUrl(key,query));url.searchParams.set('X-Amz-Expires','3600');return (await aws().sign(url.toString(),{method,aws:{signQuery:true}})).url;}
export const xmlValue=(s:string,k:string)=>s.match(new RegExp(`<${k}>([\\s\\S]*?)</${k}>`))?.[1]||'';
export const escapeXml=(s:string)=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
export async function parts(m:Match){
 if(!m.uploadId)return [];
 const result:{number:number,etag:string,size:number}[]=[];let marker='';
 do{const text=await(await s3(m.key,`?uploadId=${encodeURIComponent(m.uploadId)}${marker?'&part-number-marker='+marker:''}`)).text();result.push(...[...text.matchAll(/<Part>([\s\S]*?)<\/Part>/g)].map(x=>({number:Number(xmlValue(x[1],'PartNumber')),etag:xmlValue(x[1],'ETag').replaceAll('&quot;','"'),size:Number(xmlValue(x[1],'Size'))})));marker=xmlValue(text,'IsTruncated')==='true'?xmlValue(text,'NextPartNumberMarker'):'';}while(marker);
 return result;
}
