import { Upload, Pause } from 'lucide-react';
const size=(n:number)=>n>=1024**3?`${(n/1024**3).toFixed(1)} GB`:`${Math.round(n/1024**2)} MB`;
export function UploadProgress({uploaded,total,onPause}:{uploaded:number;total:number;onPause?:()=>void}){
 const percent=total?Math.min(100,uploaded/total*100):0;
 return <div className="upload-progress"><Upload size={32}/><h2>{total?'Saving your match':'Saving recording'}</h2>{total?<><progress aria-label="Match upload progress" value={uploaded} max={total}/><b>{size(uploaded)} of {size(total)}</b><p>{percent>0&&percent<1?'<1':Math.floor(percent)}% uploaded</p><button className="secondary pause-upload" onClick={onPause}><Pause size={16}/>Pause upload</button><p className="help">Keep this page open until uploading finishes. Processing continues after you leave.</p></>:<p>Finishing saved segments…</p>}</div>;
}
